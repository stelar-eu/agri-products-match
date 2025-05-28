import json
import sys
import traceback
from utils.mclient import MinioClient
import pandas as pd
import os
import tempfile

# Constants
REQUIRED_COLUMNS = {"N", "P", "K"}

# LANGUAGE DICTIONARY
lang_dict = {
    'italiano':   {},
    'english':    {'glyphosate':'glifosato','acetamiprid':'acetamiprid','imidacloprid':'imidacloprid'},
    'français':   {'glyphosate':'glifosate'},
    'deutsch':    {'glyphosat':'glifosato'},
    'nederlands': {'glyphosaat':'glifosato'},
    'dutch':      {'glyphosaat':'glifosato'},
    'srpski':     {'глифосат':'glifosato'},
    'español':    {'glifosato':'glifosato'},
}


def npk_distance(npk1, npk2):
    """Euclidean distance between two N‑P‑K triples."""
    return sum((a - b) ** 2 for a, b in zip(npk1, npk2)) ** 0.5

def match_fertilizers(df_npk: pd.DataFrame, df_fert: pd.DataFrame) -> pd.DataFrame:
    """Attach the closest‑match fertilizer (by N‑P‑K composition) to every user row."""

    # Guard: validate schema
    if not (REQUIRED_COLUMNS <= set(df_npk.columns) and REQUIRED_COLUMNS <= set(df_fert.columns)):
        raise ValueError(f"Both CSVs must contain columns {REQUIRED_COLUMNS}.")

    result = df_npk.copy()
    result["Fertilizzante"] = ""

    # Pre‑extract fertilizer tuples once for speed
    fert_tuples = [((row.N, row.P, row.K), row.Nome) for _, row in df_fert.iterrows()]

    for idx, row in result.iterrows():
        user_npk = (row.N, row.P, row.K)
        # Find best match
        best = min(fert_tuples, key=lambda tpl: npk_distance(user_npk, tpl[0]))
        result.at[idx, "Fertilizzante"] = best[1]

    return result


def run(json: dict):

    try:
        # --------------- MinIO initialisation ---------------
        minio_cfg = json.get("minio", {})
        mc = MinioClient(
            minio_cfg.get("endpoint_url"),
            minio_cfg.get("id"),
            minio_cfg.get("key"),
            secure=True,
            session_token=minio_cfg.get("skey"),
        )

        # --------------- Retrieve user parameters -----------
        inputs = json["input"]
        outputs = json["output"]

        npk_remote_path = inputs.get("npk_values")[0] if "npk_values" in inputs else None
        fert_remote_path = inputs.get("fertilizer_dataset")[0] if "fertilizer_dataset" in inputs else None
        pesticides_remote_path = inputs.get("pesticides_dataset")[0] if "pesticides_dataset" in inputs else None
        substance_remote_path = inputs.get("active_substances")[0] if "active_substances" in inputs else None

        output_remote_path = outputs["matched_products"]

        parameters = json.get("parameters", {})

        if parameters['mode'] == 'fertilizers':
            print("--> Running in fertilizers mode")
            # ---------------- IO: download inputs ----------------
            with tempfile.TemporaryDirectory() as tmpdir:
                local_npk = os.path.join(tmpdir, "npk.csv")
                local_fert = os.path.join(tmpdir, "fert.csv")

                if not npk_remote_path or not fert_remote_path:
                    return {
                            "message": "'npk_values' and 'fertilizer_dataset' are required inputs in fertilizers mode.",
                            "error": "Invalid Inputs",
                            "status": "error",
                    }

                mc.get_object(s3_path=npk_remote_path, local_path=local_npk)
                mc.get_object(s3_path=fert_remote_path, local_path=local_fert)

                # ---------------- Core logic --------------------
                df_npk = pd.read_csv(local_npk)
                df_fert = pd.read_csv(local_fert)
                df_out = match_fertilizers(df_npk, df_fert)

                local_out = os.path.join(tmpdir, "matched.csv")
                df_out.to_csv(local_out, index=False)

                # --------------- Upload result ------------------
                mc.put_object(s3_path=output_remote_path, file_path=local_out)

            # --------------- Build response ---------------------
            return {
                "message": "Tool executed successfully!",
                "output": {
                    "matched_fertilizers": output_remote_path,
                },
                "metrics": {
                    "records_in": len(df_npk),
                    "records_out": len(df_out),
                },
                "status": "success",
            }

        elif parameters['mode'] == 'pesticides':

            print("--> Running in pesticides mode")
            if not parameters.get("input_language") or not parameters.get("db_language"):
                return {
                    "message": "'input_language' and 'db_language' parameters are required in pesticides mode.",
                    "error": "Invalid Parameters",
                    "status": "error",
                }

            # ---------------- IO: download inputs ----------------
            with tempfile.TemporaryDirectory() as tmpdir:
                local_subst = os.path.join(tmpdir, "subst.csv")
                local_pest =  os.path.join(tmpdir, "pest.csv")

                if not pesticides_remote_path or not substance_remote_path:
                    return {
                            "message": "'pesticides_dataset' and 'active_substances' are required inputs in pesticides mode.",
                            "error": "Invalid Inputs",
                            "status": "error",
                    }

                mc.get_object(s3_path=substance_remote_path, local_path=local_subst)
                mc.get_object(s3_path=pesticides_remote_path, local_path=local_pest)

                # ---------------- Core logic --------------------
                # Read CSV files
                df_user = pd.read_csv(local_subst, dtype=str, encoding='latin-1')
                df_db = pd.read_csv(local_pest, dtype=str, encoding='latin-1', sep=';')

                # Check required columns
                if 'ACTIVE_SUBSTANCES' not in df_user.columns:
                    return {
                        "message": "Column 'ACTIVE_SUBSTANCES' missing in user CSV",
                        "error": "Missing Column",
                        "status": "error",
                    }

                for c in ['PRODOTTO', 'SOSTANZE_ATTIVE']:
                    if c not in df_db.columns:
                        return {
                            "message": f"Column '{c}' missing in DB CSV",
                            "error": "Missing Column",
                            "status": "error",
                        }
                
                # Prepare language mapping
                key = parameters.get("input_language", "italiano").strip().lower()
                mapping = lang_dict.get(key)
                if mapping is None:
                    print(f"Input language '{key}' not recognized, using Italian")
                    mapping = lang_dict['italiano']
                print(f"Matching from '{key}' to 'italiano'")

                # Matching
                results = []
                for _, row in df_user.iterrows():
                    raw = str(row['ACTIVE_SUBSTANCES']).strip()
                    target = mapping.get(raw.lower(), raw)
                    mask = df_db['SOSTANZE_ATTIVE'].str.contains(target, case=False, na=False)
                    for _, prod in df_db[mask].iterrows():
                        results.append({
                            'INPUT_SUBSTANCE': raw,
                            'PRODOTTO':        prod['PRODOTTO'],
                            'SOSTANZE_ATTIVE': prod['SOSTANZE_ATTIVE'],
                            'INPUT_LANG':      key,
                            'DB_LANG':         parameters.get("db_language", "italiano")
                        })
                
                # Write output
                if not results:
                    return {
                        "message": "No matching products found.",
                        "status": "success",
                        "output": {},
                        "metrics": {
                            "records_in": len(df_user),
                            "records_out": 0,
                        }
                    }
                else:
                    df_out = pd.DataFrame(results)
                    local_out = os.path.join(tmpdir, "matched_pesticides.csv")
                    df_out.to_csv(local_out, index=False, encoding='utf-8-sig', sep=';')

                    # --------------- Upload result ------------------
                    mc.put_object(s3_path=output_remote_path, file_path=local_out)

                    print(f"Output written: {output_remote_path} ({len(df_out)} rows)")

                    # --------------- Build response ---------------------
                    return {
                        "message": "Tool executed successfully!",
                        "output": {
                            "matched_pesticides": output_remote_path,
                        },
                        "metrics": {
                            "records_in": len(df_user),
                            "records_out": len(df_out),
                        },
                        "status": "success",
                    }

        else:
            return {
                "message": "Supported modes are 'fertilizers' and 'pesticides'. Include 'mode' in parameters.",
                "error": "Invalid Mode",
                "status": "error",
            }

    except Exception:
        print(traceback.format_exc())
        return {
            "message": "An error occurred during fertilizer matching.",
            "error": traceback.format_exc(),
            "status": "error",
        }

if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise ValueError("Please provide 2 files.")
    with open(sys.argv[1]) as o:
        j = json.load(o)
    response = run(j)
    with open(sys.argv[2], 'w') as o:
        o.write(json.dumps(response, indent=4))
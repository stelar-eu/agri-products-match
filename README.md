# Agri Products Match 

A Python tool that matches user-provided fertilizers or pesticides to known agricultural products using language-specific mappings. 

This version of agri-products-match has been made compatible with the KLMS Tool Template and can be incorporated withing workflows. The tool is invoked in the form of a Task within a workflow Process via the respective API call. 

## Tool Invocation Example

An example spec for executing an autonomous instance the tool in NPK-match mode through the API would be:

```json
{
    "process_id": "f9645b89-34e4-4de2-8ecd-dc10163d9aed",
    "name": "Agri Products Match",
    "image": "petroud/agri-products-match:latest",
    "inputs": {
        "npk_values": [
            "325fb7c7-b269-4a1e-96f6-a861eb2fe325"
        ],
        "fertilizer_dataset":[
            "41da3a81-3768-47db-b7ac-121c92ec3f6d"
        ]
    },
    "datasets": {
        "d0": "2f8a651b-a40b-4edd-b82d-e9ea3aba4d13"
    },
    "parameters": {
        "mode": "fertilizers"
    },
    "outputs": {
        "matched_fertilizers": {
            "url": "s3://abaco-bucket/MATCH/matched_fertilizers.csv",
            "dataset": "d0",
            "resource": {
                "name": "Matched Fertilizers based on NPK values",
                "relation": "matched"
            }
        }
    }
}
```

An example spec for executing an autonomous instance the tool in Pesticides Match mode through the API would be:

```json
{
    "process_id": "f9645b89-34e4-4de2-8ecd-dc10163d9aed",
    "name": "Agri Products Match",
    "image": "petroud/agri-products-match:latest",
    "inputs": {
        "active_substances": [
            "a331d9ae-cd17-474c-b323-d4fb3bdcadfe"
        ],
        "pesticides_dataset":[
            "cf7fac9e-db36-4e97-8b44-e23404170a1f"
        ]
    },
    "datasets": {
        "d0": "45c94866-a07e-46ce-829e-79a05307ac82"
    },
    "parameters": {
        "mode": "pesticides",
        "input_language": "italiano",
        "db_language": "italiano"
    },
    "outputs": {
        "matched_products": {
            "url": "s3://abaco-bucket/MATCH/matched_pesticides.csv",
            "dataset": "d0",
            "resource": {
                "name": "Matched Pesticides based on active substances values",
                "relation": "matched"
            }
        }
    }
}
```

## Tool Input JSON
At runtime the tool expects the following, translated by the API in NPK mode, JSON: 
```json

{
        "input": {
            "fertilizer_dataset": [
                "s3://abaco-bucket/MATCH/BancaDatiMinisteriale_Fitosanitari.CSV"
            ],
            "npk_values": [
                "s3://abaco-bucket/MATCH/user_NPK_values.csv"
            ]
        },
        "parameters":{
            "mode": "fertilizers",
        },
        "minio": {
            "endpoint_url": "https://minio.stelar.gr",
            "id": "XXXXXXXXXXX",
            "key": "XXXXXXXXXXX",
            "skey": "XXXXXXXXXXX"
        },
        "output": {
            "matched_products": "s3://abaco-bucket/MATCH/matched_fertilizers.csv"
        },
        "parameters": {}
    }
```
### `input`
The tool expect two inputs during runtime that are being utilized in conjuction during the calculation:
- `fertilizer_dataset` (CSV): User-supplied nutrient targets for individual fields, crops, or recommendation scenarios.	
- `npk_values` (CSV): Master list of fertilizers with guaranteed nutrient analyses.	



At runtime the tool expects the following, translated by the API in Pesticides mode, JSON: 
```json
{
        "input": {
            "active_substances": [
                "s3://abaco-bucket/MATCH/user_ACTIVE_SUBSTANCES_values.csv"
            ],
            "pesticides_dataset":[
                "s3://abaco-bucket/MATCH/Dataset_Banca_Dati_Fertilizzanti.csv"
            ]
        },
        "parameters":{
            "mode": "pesticides",
            "input_language": "italiano",
            "db_language":  "italiano"
        },
        "minio": {
            "endpoint_url": "https://minio.stelar.gr",
            "id": "XXXXXXXXXXX",
            "key": "XXXXXXXXXXX",
            "skey": "XXXXXXXXXXX"
        },
        "output": {
            "matched_products": "s3://abaco-bucket/MATCH/matched_fertilizers.csv"
        },
        "parameters": {}
    }
```
### `input`
The tool expect two inputs during runtime that are being utilized in conjuction during the calculation:
- `active_substances` (CSV): User-supplied list of active chemical substances intended for matching against known pesticide products.
- `pesticides_dataset` (CSV): A master dataset containing known pesticide products and their associated active substances, used as a reference for matching. The language matches the parameters provided.



### `output`
Upon the input files provided the tool concludes to a file representing the most suitable product. The result is in CSV form and stored in the path defined by the `match_products` output key. 

## Tool Output JSON

```json
{
    "message": "Tool executed successfully!",
    "output": {
        "matched_products": "s3://abaco-bucket/MATCH/matched_products.csv"
    },
    "metrics": {
        "records_in": 10,
        "records_out": 10
    },
    "status": "success"
}
```


## How to build 
Alter the `IMGTAG` in Makefile with a repository from your Image Registry and hit 
`make` in your terminal within the same directory.
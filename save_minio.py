# Save data on a Minio backend
from minio import Minio

def minio_upload(config_dict: dict, filename: str, target: str = "CLOUD"):
    """
    Function to load a file into Minio

    Parameters:
    config_dict (dict): dictionary with configuration for Minio
                        object storage
    filename (str): string with the local name of the file. It
                    will be the same on Minio
    target (str):   string with information on the dictionary
                    section where to get Minio configuration

    Returns:
    response_h (bool): True if file was uploaded, else False

    """
    mclient = Minio(
        config_dict.get(target).get("minio_url"),
        access_key=config_dict.get(target).get("minio_account"),
        secret_key=config_dict.get(target).get("minio_key"),
    )
    try:
        response_h = mclient.fput_object(
            config_dict.get(target).get("bucket"),
            filename,
            filename,
            content_type="application/csv",
        )
    except:
        response_h = False
    return bool(response_h)

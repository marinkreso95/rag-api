from typing import List, BinaryIO
from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceNotFoundError, ResourceExistsError


class AzureBlobStorageService:
    def __init__(
        self,
        container_name: str,
        connection_string: str | None = None,
        account_url: str | None = None,
        credential=None,
    ):
        if connection_string:
            self.blob_service = BlobServiceClient.from_connection_string(
                connection_string,
                api_version="2021-12-02"
            )
        elif account_url and credential:
            self.blob_service = BlobServiceClient(
                account_url=account_url,
                credential=credential,
                api_version="2021-12-02"
            )
        else:
            raise ValueError("Invalid Azure Blob Storage configuration")

        self.container_client = self.blob_service.get_container_client(container_name)

        try:
            self.container_client.create_container()
        except ResourceExistsError:
            pass

    def upload(self, blob_name: str, data: bytes) -> None:
        blob_client = self.container_client.get_blob_client(blob_name)
        blob_client.upload_blob(data, overwrite=True)

    def download(self, blob_name: str) -> bytes:
        blob_client = self.container_client.get_blob_client(blob_name)

        try:
            return blob_client.download_blob().readall()
        except ResourceNotFoundError:
            raise FileNotFoundError(blob_name)

    def delete(self, blob_name: str) -> None:
        blob_client = self.container_client.get_blob_client(blob_name)

        try:
            blob_client.delete_blob()
        except ResourceNotFoundError:
            raise FileNotFoundError(blob_name)

    def list(self, prefix: str | None = None) -> List[str]:
        """
        Optionally list blobs under a virtual folder using prefix.
        """
        return sorted(
            blob.name
            for blob in self.container_client.list_blobs(name_starts_with=prefix)
        )

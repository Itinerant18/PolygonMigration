# Azure upload disabled. Google Drive is used for storage now.
# The code below is kept for reference and can be restored if needed.
# import os
# from azure.identity import UsernamePasswordCredential
# from azure.storage.blob import BlobServiceClient
# from azure.core.exceptions import ResourceNotFoundError, ClientAuthenticationError
import os
import logging

logger = logging.getLogger(__name__)

class AzureBlobManager:
    """
    A manager class to handle read/write operations for Azure Blob Storage using user credentials.

    Provides methods to upload and delete test cases as blobs in Azure Storage.
    """
    def __init__(self, account_url, tenant_id, client_id, username, password):
        """
        Initializes the Blob Service Client using user credentials.

        Args:
            account_url (str): The URL of the Azure Storage Account.
            tenant_id (str): The Azure Active Directory Tenant ID.
            client_id (str): The Client ID of an AAD application.
            username (str): The user's email/login name.
            password (str): The user's password.

        Raises:
            ClientAuthenticationError: If authentication fails.
            Exception: For other unexpected errors during initialization.
        """
        self.account_url = account_url
        self.blob_service_client = None
        
        # Azure upload disabled. Google Drive is used for storage now.
        # credential = UsernamePasswordCredential(
        #     tenant_id=tenant_id,
        #     client_id=client_id,
        #     username=username,
        #     password=password
        # )
        # self.blob_service_client = BlobServiceClient(
        #     account_url=self.account_url,
        #     credential=credential
        # )
        raise Exception("Azure upload is disabled. Google Drive is used for storage now.")

    def upload_test_case(self, container_name, db_problem_id, test_number, input_data, output_data):
        """
        Uploads a test case's input and output to Azure Blob Storage as separate blobs.

        Args:
            container_name (str): The name of the container.
            db_problem_id (str|int): The database problem ID (not Polygon ID).
            test_number (int): The test case number (1-based).
            input_data (str): The input data as a string.
            output_data (str): The output data as a string.

        Returns:
            None
        """
        # Azure upload disabled. Google Drive is used for storage now.
        # input_blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=input_blob_name)
        # input_blob_client.upload_blob(input_data.encode('utf-8'), overwrite=True)
        # output_blob_client = self.blob_service_client.get_blob_client(container=container_name, blob=output_blob_name)
        # output_blob_client.upload_blob(output_data.encode('utf-8'), overwrite=True)
        raise Exception("Azure upload is disabled. Google Drive is used for storage now.")

    def empty_blob(self, container_name, problem_id):
        """
        Deletes all blobs for a given problem_id from Azure Blob Storage in the specified container.

        Args:
            container_name (str): The name of the container.
            problem_id (str|int): The problem ID (database problem ID).

        Returns:
            None
        """
        # Azure upload disabled. Google Drive is used for storage now.
        # prefix = f"test_cases/{problem_id}/"
        # container_client = self.blob_service_client.get_container_client(container_name)
        # blobs_to_delete = [blob.name for blob in container_client.list_blobs(name_starts_with=prefix)]
        # for blob_name in blobs_to_delete:
        #     container_client.delete_blob(blob_name)
        raise Exception("Azure upload is disabled. Google Drive is used for storage now.")
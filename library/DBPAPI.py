from urllib.parse import urlencode
import base64

import requests
from suds.client import Client
from suds.transport.http import HttpAuthenticated

from entities import parcel, address, recipient, sender, shipment, account, account_balance, address_key


class DespatchBayAPI(object):

    def __init__(self, apiuser, apikey):
        # todo: set differently
        url = 'http://api.despatchbay.st'
        soap_path = '/soap/%s/%s?wsdl'
        documents_path = '/documents/v1/'
        account_url = url + soap_path % ('v15', 'account')
        shipping_url = url + soap_path % ('v15', 'shipping')
        addressing_url = url + soap_path % ('v15', 'addressing')
        tracking_url = url + soap_path % ('v15', 'tracking')
        t1 = HttpAuthenticated(username=apiuser, password=apikey)
        t2 = HttpAuthenticated(username=apiuser, password=apikey)
        t3 = HttpAuthenticated(username=apiuser, password=apikey)
        t4 = HttpAuthenticated(username=apiuser, password=apikey)
        self.accounts_client = Client(account_url,  transport=t1)
        self.addressing_client = Client(addressing_url,  transport=t2)
        self.shipping_client = Client(shipping_url,  transport=t3)
        self.tracking_client = Client(tracking_url,  transport=t4)
        self.labels_url = url + documents_path + 'labels'
        self.manifest_url = url + documents_path + 'manifest'
        print(addressing_url)

    # Shipping entities

    def parcel(self, **kwargs):
        """
        Creates a dbp parcel entity
        """
        return parcel.Parcel(self.shipping_client, **kwargs)

    def address(self, **kwargs):
        """
        Creates a dbp address entity
        """
        return address.Address(self.shipping_client, **kwargs)

    def recipient(self, **kwargs):
        """
        Creates a dbp recipient address entity
        """
        return recipient.Recipient(self.shipping_client, **kwargs)

    def sender(self, **kwargs):
        """
        Creates a dbp sender address entity
        """
        return sender.Sender(self.shipping_client, **kwargs)

    def shipment(self, **kwargs):
        """
        Creates a dbp shipment entity
        """
        return shipment.Shipment(self.shipping_client, **kwargs)

    # Account Services

    def get_account(self):
        account_data = self.accounts_client.service.GetAccount()
        account_dict = self.accounts_client.dict(account_data)
        account_object = account.Account.from_dict(self.accounts_client, **account_dict)
        return account_object

    def get_account_balance(self):
        balance_data = self.accounts_client.service.GetAccountBalance()
        balance_dict = self.accounts_client.dict(balance_data)
        balance_object = account_balance.AccountBalance.from_dict(
            self.accounts_client,
            **balance_dict)
        return balance_object

    def get_sender_addresses(self):
        sender_addresses_data = self.accounts_client.service.GetSenderAddresses()
        sender_addresses_dict_list = []
        for sender_address in sender_addresses_data:
            sender_address_dict = self.accounts_client.dict(sender_address)
            sender_addresses_dict_list.append(sender.Sender.from_dict(
                self.accounts_client,
                **sender_address_dict))
        return sender_addresses_dict_list

    # Addressing Services

    def find_address(self, postcode, property):
        found_address = self.addressing_client.service.FindAddress(postcode, property)
        found_address_dict = self.addressing_client.dict(found_address)
        found_address_object = address.Address.from_dict(
            self.addressing_client,
            **found_address_dict
        )
        return found_address_object

    def get_address_by_key(self, key):
        found_address = self.addressing_client.service.GetAddressByKey(key)
        found_address_dict = self.addressing_client.dict(found_address)
        found_address_object = address.Address.from_dict(
            self.addressing_client,
            **found_address_dict
        )
        return found_address_object

    def get_address_keys_by_postcode(self, postcode):
        address_key_return = self.addressing_client.service.GetAddressKeysByPostcode(postcode)
        address_keys_dict_list = []
        for soap_address_key in address_key_return:
            address_key_dict = self.accounts_client.dict(soap_address_key)
            address_keys_dict_list.append(address_key.AddressKey.from_dict(
                self.addressing_client,
                **address_key_dict))
        return address_keys_dict_list

    # Shipping services

    def get_available_services(self, shipment_request):
        return self.shipping_client.service.GetAvailableServices(
            shipment_request.to_soap_object())

    def get_collection(self, collection_id):
        return self.shipping_client.service.GetCollection(collection_id)

    def get_collections(self):
        return self.shipping_client.service.GetCollections()

    def get_available_collection_dates(self, sender_address, courier_id):
        return self.shipping_client.service.GetAvailableCollectionDates(
            sender_address.to_soap_object(), courier_id)

    def get_shipment(self, shipment_id):
        return self.shipping_client.service.GetShipment(shipment_id)

    def add_shipment(self, shipment_request):
        return self.shipping_client.service.AddShipment(shipment_request.to_soap_object())

    def book_shipments(self, shipment_ids):
        return self.shipping_client.service.BookShipments(shipment_ids)

    def cancel_shipment(self, shipment_id):
        return self.shipping_client.service.CancelShipment(shipment_id)

    # Tracking services

    def get_tracking(self, tracking_number):
        return self.tracking_client.service.GetTracking(tracking_number)

    # Labels services

    def download_shipment_labels(self, ship_collect_ids, download_path, layout=None,
                                 label_format=None, label_dpi=None):
        if isinstance(ship_collect_ids, list):
            shipment_string = ','.join(ship_collect_ids)
        else:
            shipment_string = ship_collect_ids
        query_dict = {}
        if layout:
            query_dict['layout'] = layout
        if label_format:
            query_dict['format'] = label_format
            if label_format == 'png_base64' and label_dpi:
                query_dict['dpi'] = label_dpi
        label_request_url = '{}/{}'.format(self.labels_url,
                                           shipment_string)
        if query_dict:
            query_string = urlencode(query_dict)
            label_request_url = label_request_url + '?' + query_string
        r = requests.get(label_request_url)
        if label_format == 'png_base64' or label_format == 'pdf_base64':
            label_data = base64.b64decode(r.content)
        else:
            label_data = r.content
        with open(download_path, 'wb') as label_file:
            label_file.write(label_data)

    def download_manifest(self, collection_id, download_path, manifest_format=None):
        query_dict = {}
        if manifest_format:
            query_dict['format'] = manifest_format
        manifest_request_url = '{}/{}'.format(self.manifest_url,
                                              collection_id)
        if query_dict:
            query_string = urlencode(query_dict)
            manifest_request_url = manifest_request_url + '?' + query_string
        r = requests.get(manifest_request_url)
        if manifest_format == 'base64':
            manifest_data = base64.b64decode(r.content)
        else:
            manifest_data = r.content
        with open(download_path, 'wb') as manifest_file:
            manifest_file.write(manifest_data)


#!/usr/bin/env python3
#
# Description: Flexible Flocker REST API Client
# License: LGPLv2
# Maintainer: Srdjan Grubor <sgnn7@sgnn7.org>

import http.client
import inspect
import json
import os
import ssl
import tempfile

class FlockerApi(object):
    DEFAULT_PLUGIN_DIR = os.environ.get('CERT_DIR', '/etc/flocker')

    def __init__(self, api_version = 1, debug = False):
        control_service = os.environ.get("CONTROL_SERVICE", "localhost")
        control_port = os.environ.get("CONTROL_PORT", 4523)

        self._api_version = api_version
        self._debug = debug
        self._last_known_config = None

        key_file = os.environ.get("KEY_FILE", "%s/plugin.key" % self.DEFAULT_PLUGIN_DIR)
        cert_file = os.environ.get("CERT_FILE", "%s/plugin.crt" % self.DEFAULT_PLUGIN_DIR)
        ca_file = os.environ.get("CA_FILE", "%s/cluster.crt" % self.DEFAULT_PLUGIN_DIR)

        # Create a certificate chain and then pass that into the SSL system.
        cert_with_chain_tempfile = tempfile.NamedTemporaryFile()

        temp_cert_with_chain_path = cert_with_chain_tempfile.name
        os.chmod(temp_cert_with_chain_path, 0o0600)

        # Write our cert and append the CA cert to build the chain
        with open(cert_file, 'rb') as cert_file_obj:
            cert_with_chain_tempfile.write(cert_file_obj.read())

        cert_with_chain_tempfile.write('\n'.encode('utf-8'))

        with open(ca_file, 'rb') as cacert_file_obj:
            cert_with_chain_tempfile.write(cacert_file_obj.read())

        # Reset file pointer for the SSL context to read it properly
        cert_with_chain_tempfile.seek(0)

        ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
        ssl_context.load_cert_chain(temp_cert_with_chain_path, key_file)

        self._http_client = http.client.HTTPSConnection(control_service,
                                                        control_port,
                                                        context=ssl_context)

    # XXX: These should really be generic functions created dynamically
    def get(self, endpoint, data = None):
        return self._make_api_request('GET',
                                      "/v%s/%s" % (self._api_version, endpoint),
                                      data)

    def post(self, endpoint, data = None):
        return self._make_api_request('POST',
                                      "/v%s/%s" % (self._api_version, endpoint),
                                      data)

    def delete(self, endpoint, data = None):
        return self._make_api_request('DELETE',
                                      "/v%s/%s" % (self._api_version, endpoint),
                                      data)

    def _make_api_request(self, method, endpoint, data = None):
      # Convert data to string if it's not yet in this format
      if data and not isinstance(data, str):
          data = json.dumps(data).encode('utf-8')

      headers = { 'Content-type': 'application/json' }
      if self._last_known_config:
          headers['X-If-Configuration-Matches'] = self._last_known_config

      self._http_client.request(method, endpoint, data,
                                headers=headers)

      response = self._http_client.getresponse()

      status =  response.status
      body =  response.read()

      # Make sure to use the X
      if 'X-Configuration-Tag' in response.getheaders():
          self._last_known_config = response.getheaders()['X-Configuration-Tag'].decode('utf-8')

      print('Status:', status)

      # If you want verbose debugging
      # print('Body:', body)

      print()

      result = json.loads(body.decode('utf-8'))

      if self._debug == True:
          print(json.dumps(result, sort_keys=True, indent=4))

      return result

    # XXX: Dummy decorator that allows us to indicate what methods are part
    #      of the CLI
    def cli_method(func):
        return func

    # XXX: Yeah it's gnarly :(
    # TODO: Get a better way to introspect that's not a static array
    def get_methods(self):
        source = inspect.getsourcelines(FlockerApi)[0]
        for index, line in enumerate(source):
            line = line.strip()
            if line.strip() == '@cli_method':
                nextLine = source[ index + 1 ]
                name = nextLine.split('def')[1].split('(')[0].strip()
                yield(name)

    # Specific API requests
    @cli_method
    def get_version(self):
      """
      Gets version of the Flocker service
      """
      version = self.get('version')
      return version['flocker']

    @cli_method
    def create_volume(self, name, size_in_gb, primary_id, profile = None):
        if not isinstance(size_in_gb, int):
            size_in_gb = int(size_in_gb)

        data = {
            'primary': primary_id,
            'maximum_size': size_in_gb << 30,
            'metadata': {
               'name': name
            }
        }

        if profile:
            data['metadata']['clusterhq:flocker:profile'] = profile

        return self.post('configuration/datasets', data)


    @cli_method
    def move_volume(self, volume_id, new_primary_id):
        data = { 'primary': new_primary_id }
        return self.post('configuration/datasets/%s' % volume_id, data)

    @cli_method
    def delete_volume(self, dataset_id):
        return self.delete('configuration/datasets/%s' % dataset_id)

    @cli_method
    def list_volumes(self):
        return self.get('configuration/datasets')

    @cli_method
    def list_nodes(self):
        return self.get('state/nodes')

    @cli_method
    def list_leases(self):
        return self.get('configuration/leases')

    @cli_method
    def release_lease(self, dataset_id):
        return self.delete('configuration/leases/%s' % dataset_id)

    @cli_method
    def acquire_lease(self, dataset_id, node_id, expires = None):
        data = { 'dataset_id': dataset_id,
                 'node_uuid': node_id,
                 'expires': expires }
        return self.post('configuration/leases', data)

if __name__ == '__main__':
    # We only parse args if we're invoked as a script
    import argparse
    api = FlockerApi(debug = True)

    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest='action')

    # Dynamically add all relevant cli methods
    for method_name in api.get_methods():
        func = getattr(api, method_name)
        help_doc = func.__doc__ or "No documentation"
        help_line = '%s. See "%s -help" for more options' % (help_doc, method_name)
        args = inspect.getargspec(func)

        parser_for_method = subparsers.add_parser(method_name, help = help_line)
        # Mandatory args
        for index, arg in enumerate(args.args):
            # Skip 'self'
            if index == 0:
                continue

            # Divide into things with defaults and things without
            if index < len(args.args) - len(args.defaults or []):
                parser_for_method.add_argument(arg)
            else:
                parser_for_method.add_argument('--%s' % arg, default=args.defaults[len(args.args) - index - 1])

    parsed_args = parser.parse_args()

    action = parsed_args.action

    print("Action:", parsed_args.action)

    func = getattr(api, action)
    args = inspect.getargspec(func)
    args_to_send = []
    for index, arg in enumerate(args.args):
        # Skip 'self'
        if index == 0:
            continue

        args_to_send.append(vars(parsed_args)[arg])
    print('Args:', args_to_send)
    func(*args_to_send)

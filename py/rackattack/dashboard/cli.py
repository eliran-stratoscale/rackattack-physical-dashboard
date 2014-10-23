from rackattack import clientfactory

client = clientfactory.factory()
import pprint
pprint.pprint(client.call('admin__queryStatus'))

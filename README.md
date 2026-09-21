## pyvcloud

[![License](https://img.shields.io/pypi/l/pyvcloud.svg)](https://pypi.python.org/pypi/pyvcloud) [![Stable Version](https://img.shields.io/pypi/v/pyvcloud.svg)](https://pypi.python.org/pypi/pyvcloud) [![Build Status](https://img.shields.io/travis/vmware/pyvcloud.svg?style=flat)](https://travis-ci.org/vmware/pyvcloud/)

`pyvcloud` is the Python SDK for VMware vCloud Director.

Supported API versions are 29.0, 30.0, 31.0, 32.0, 33.0, 34.0, 35.0, 36.0,
37.0, 37.1, and 37.2.

API 37.2 corresponds to [VMware Cloud Director 10.4.2](https://docs.vmware.com/en/VMware-Cloud-Director/10.4.2/rn/vmware-cloud-director-1042-release-notes/index.html).
Both `Client` and `VcdClient` automatically select the highest non-deprecated
production API version supported by the server and this SDK. To explicitly
select API 37.2, pass `api_version=ApiVersion.VERSION_37_2.value` (or `'37.2'`)
to the client constructor:

```python
from pyvcloud.vcd.client import ApiVersion, Client

client = Client('https://vcd.example.com',
                api_version=ApiVersion.VERSION_37_2.value)
```

## Installation

In general, `pyvcloud` can be installed with the following command:
```shell
$ pip install --user pyvcloud
```
Depending on your operating system and distribution you
may need additional packages to install successfully. See
[install.md](docs/install.md) for full details.

## Testing

Contributions to `pyvcloud` are welcome and it should include unit tests. See the [contributing guide](CONTRIBUTING.md) for details.

Run the offline unit tests without a VCD server or credentials:

```shell
python -m unittest discover -s tests -p 'test_*.py'
```

`tox` runs these tests and the SDK's style checks. The integration tests below
require a configured VCD server.

Check out the latest version and install:

```shell
git clone https://github.com/vmware/pyvcloud.git
cd pyvcloud
virtualenv .venv
source .venv/bin/activate
python setup.py develop
```

Sample test parameters are in file [tests/config.yml](tests/config.yml). Create a copy to specify your own settings and use the `VCD_TEST_CONFIG_FILE` env variable.

```shell
cd tests
cp config.yml private.config.yml
# customize credentials and other parameters
export VCD_TEST_CONFIG_FILE=private.config.yml
# run unit test
python -m unittest vcd_login vcd_catalog_setup
# run just a test method
python -m unittest vcd_catalog_setup.TestCatalogSetup.test_validate_ova
```

See [tests](tests/) for a list of current unit tests written for the new SDK implementation.


## Notes

Please note that this project is under development and the interfaces might change over time.

`pyvcloud` is used by [vcd-cli](https://vmware.github.io/vcd-cli), the Command Line Interface for VMware vCloud Director. It requires Python 3.6 or higher.

Previous versions and deprecated code can be found in this repository under [tag 18.2.2](https://github.com/vmware/pyvcloud/tree/18.2.2).

## Contributing

The `pyvcloud` project team welcomes contributions from the community. Before you start working with `pyvcloud`, please read our [Developer Certificate of Origin](https://cla.vmware.com/dco). All contributions to this repository must be signed as described on that page. Your signature certifies that you wrote the patch or have the right to pass it on as an open-source patch. For more detailed information, refer to [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[Apache-2.0](LICENSE.txt)

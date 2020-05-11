"""
DockerEdge Blueprint

"""

import os

#keeping verbose list of imports for reference only 
#use shortcut if importing a bunch of builtins
#from calm.dsl.builtins import *

from calm.dsl.builtins import ref, basic_cred
from calm.dsl.builtins import action, parallel
from calm.dsl.builtins import CalmTask
from calm.dsl.builtins import CalmVariable
from calm.dsl.builtins import Service, Package, Substrate
from calm.dsl.builtins import Deployment, Profile, Blueprint
from calm.dsl.builtins import provider_spec, read_provider_spec, read_local_file

# Get env variables
# read_env() reads from .env file present in blueprint top-level
# directory and returns a dict of blueprint env variables and os env variables.
# If it does not exist, it returns a dict of os env present in os.environ.
# Custom env file location can also be given with relpath param.
# relpath will look for file relative to blueprint top-level directory.
# Examples:
#   read_env()
#   read_env(relpath=".env2")
#   read_env(relpath="env/dev")

ENV = read_env()

CENTOS_USER = ENV.get("CENTOS_USER", "centos")
CENTOS_IMAGE_SOURCE = ENV.get(
    "CENTOS_IMAGE_SOURCE", "http://download.nutanix.com/calm/CentOS-7-x86_64-1810.qcow2"
)
CENTOS_SSH_PRIVATE_KEY_NAME = ENV.get("CENTOS_SSH_PRIVATE_KEY_NAME", "centos")
CENTOS_SSH_PUBLIC_KEY_NAME = ENV.get("CENTOS_SSH_PUBLIC_KEY_NAME", "centos_pub")

AHV_NIC_NAME = ENV.get("AHV_NIC_NAME", "vlan.0")
AHV_MEM = ENV.get("AHV_MEM", "4")

KAFKA_URL = ENV.get(
    "KAFKA_URL", "http://www-us.apache.org/dist/kafka/2.5.0/kafka_2.12-2.5.0.tgz"
)
ZOOKEEPER_DATA_DIR = ENV.get("ZOOKEEPER_DATA_DIR", "/home/centos/zookeepeer/data/")
KAFKA_LOG_DIRS = ENV.get("KAFKA_LOG_DIRS", "/var/log/kafka-logs")
NUMBER_OF_PARTITION = ENV.get("NUMBER_OF_PARTITION", "2")
NUMBER_OF_NODES = ENV.get("NUMBER_OF_NODES", "3")


# SSH Credentials
# read_local_file() reads file from .local folder.
# If it does not exist, it reads from [LOCAL_DIR] location given in ~/.calm/init.ini.

CENTOS_KEY = read_local_file(CENTOS_SSH_PRIVATE_KEY_NAME)
CENTOS_PUBLIC_KEY = read_local_file(CENTOS_SSH_PUBLIC_KEY_NAME)
CENTOS_CRED = basic_cred(
    CENTOS_USER, CENTOS_KEY, name="Centos", type="KEY", default=True,
)

# OS Image details for VM
CENTOS_PACKAGE = vm_disk_package(
    name="centos_disk", config={"image": {"source": CENTOS_IMAGE_SOURCE}},
)


#Passwords, tokens, and keys
EDGENODE_PASSWD = read_local_file("edgenode_passwd")
HOSTOS_PASSWD = read_local_file("hostos_passwd")
SECRETS_TOKEN = read_local_file("secrets_token")
#OBJECT_KEYS = read_local_file("object_keys")

edgenodeCreds = basic_cred("admin", ERA_PASSWD, name="era_creds")
ObjectsCreds = basic_cred("poseidon_access", OBJECT_PASSWD, name="objects_creds")
hostosCreds = basic_cred("centos", CENTOS_PASSWD, name="centos_creds", default=True)
PCCreds = basic_cred("admin", PC_PASSWD, name="pc_creds")




ERA_PASSWD = read_local_file("era_passwd")
OBJECT_PASSWD = read_local_file("object_passwd")
CENTOS_PASSWD = read_local_file("centos_passwd")
PC_PASSWD = read_local_file("pc_passwd")
DB_PASSWD = read_local_file("db_passwd")

EraCreds = basic_cred("admin", ERA_PASSWD, name="era_creds")
ObjectsCreds = basic_cred("poseidon_access", OBJECT_PASSWD, name="objects_creds")
CentOsCreds = basic_cred("centos", CENTOS_PASSWD, name="centos_creds", default=True)
PCCreds = basic_cred("admin", PC_PASSWD, name="pc_creds")

CENTOS_PASSWD = read_local_file("passwd")

DefaultCred = basic_cred("centos", CENTOS_PASSWD, name="default cred", default=True)


class EdgeNode_Host(Service):
    """ EdgeNode_Host service"""

    @action
    def __create__():
        CalmTask.Exec.ssh(name="ConfigureMaster", filename="scripts/ConfigureMaster.sh")

    @action
    def __start__():
        CalmTask.Exec.ssh(
            name="StartMasterServices", filename="scripts/StartMasterServices.sh"
        )


class Hadoop_Slave(Service):
    """Hadoop_Slave service"""

    @action
    def __create__():
        CalmTask.Exec.ssh(name="ConfigureSlave", filename="scripts/ConfigureSlave.sh")

    @action
    def __start__():
        CalmTask.Exec.ssh(
            name="StartSlaveServices", filename="scripts/StartSlaveServices.sh"
        )


class Hadoop_Master_Package(Package):
    """Hadoop Master package"""

    services = [ref(Hadoop_Master)]

    @action
    def __install__():
        CalmTask.Exec.ssh(
            name="PackageInstallTask", filename="scripts/master_PackageInstallTask.sh"
        )


class Hadoop_Slave_Package(Package):
    """Hadoop Slave package"""

    services = [ref(Hadoop_Slave)]

    @action
    def __install__():
        CalmTask.Exec.ssh(
            name="PackageInstallTask", filename="scripts/slave_PackageInstallTask.sh"
        )


class Hadoop_Master_AHV(Substrate):
    """Hadoop Master Substrate"""

    provider_spec = read_provider_spec("ahv_spec.yaml")
    provider_spec.spec["name"] = "Hadoop_Master-@@{calm_array_index}@@-@@{calm_time}@@"
    readiness_probe = {
        "disabled": False,
        "delay_secs": "0",
        "connection_type": "SSH",
        "connection_port": 22,
        "credential": ref(DefaultCred),
    }


class Hadoop_Slave_AHV(Substrate):
    """Hadoop Slave Substrate"""

    provider_spec = read_provider_spec("ahv_spec.yaml")
    provider_spec.spec["name"] = "Hadoop_Slave-@@{calm_array_index}@@-@@{calm_time}@@"
    readiness_probe = {
        "disabled": False,
        "delay_secs": "0",
        "connection_type": "SSH",
        "connection_port": 22,
        "credential": ref(DefaultCred),
    }


class Hadoop_Master_Deployment(Deployment):
    """Hadoop Master Deployment"""

    packages = [ref(Hadoop_Master_Package)]
    substrate = ref(Hadoop_Master_AHV)


class Hadoop_Slave_Deployment(Deployment):
    """Hadoop Slave Deployment"""

    min_replicas = "2"
    max_replicas = "5"

    packages = [ref(Hadoop_Slave_Package)]
    substrate = ref(Hadoop_Slave_AHV)


class Nutanix(Profile):
    """Hadoop Profile"""

    deployments = [Hadoop_Master_Deployment, Hadoop_Slave_Deployment]

    @action
    def ScaleOutSlaves():
        COUNT = CalmVariable.Simple.int("1", is_mandatory=True, runtime=True)  # noqa
        CalmTask.Scaling.scale_out(
            "@@{COUNT}@@", target=ref(Hadoop_Slave_Deployment), name="ScaleOutSlaves"
        )

    @action
    def ScaleInSlaves():
        COUNT = CalmVariable.Simple.int("1", is_mandatory=True, runtime=True)  # noqa
        CalmTask.Scaling.scale_in(
            "@@{COUNT}@@", target=ref(Hadoop_Slave_Deployment), name="ScaleInSlaves"
        )


class HadoopDslBlueprint(Blueprint):
    """* [Hadoop Master Name Node Dashboard](http://@@{Hadoop_Master.address}@@:50070)
* [Hadoop Master Data Node Dashboard](http://@@{Hadoop_Master.address}@@:8088)
    """

    credentials = [DefaultCred]
    services = [Hadoop_Master, Hadoop_Slave]
    packages = [Hadoop_Master_Package, Hadoop_Slave_Package]
    substrates = [Hadoop_Master_AHV, Hadoop_Slave_AHV]
    profiles = [Nutanix]


def main():
    print(HadoopDslBlueprint.json_dumps(pprint=True))


if __name__ == "__main__":
    main()

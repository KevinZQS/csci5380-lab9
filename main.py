from network_setup import setup_virtual_networks
from security_setup import setup_security_group
from instance_setup import create_lab_instances
from frr_setup import deploy_frr_service
from ryu_setup import deploy_ryu_service


def main():
    print("=== Lab 9 Automation Start ===\n")

    print("[1/5] Virtual network setup")
    setup_virtual_networks()
    print()

    print("[2/5] Security group setup")
    setup_security_group()
    print()

    print("[3/5] Instance setup")
    create_lab_instances()
    print()

    print("[4/5] FRR container setup")
    deploy_frr_service()
    print()

    print("[5/5] Ryu container setup")
    deploy_ryu_service()
    print()

    print("=== Lab 9 Automation Complete ===")


if __name__ == "__main__":
    main()
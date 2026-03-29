import os
import time
import docker

BRIDGE_NAME = "bgp-net"

SDN_CONTROLLER_CONTAINER = "lab9-ryu"
SDN_CONTROLLER_IP = "192.168.50.5"
LOCAL_BGP_AS = 65020
LOCAL_ROUTER_ID = "3.3.3.3"

PEER_IP = "192.168.50.3"
PEER_AS = 65001

CONTROLLER_APP_DIR = "/tmp/lab9_ryu"

docker_client = docker.from_env()


def ensure_controller_app_dir():
    os.makedirs(CONTROLLER_APP_DIR, exist_ok=True)
    init_file = os.path.join(CONTROLLER_APP_DIR, "__init__.py")
    if not os.path.exists(init_file):
        with open(init_file, "w") as f:
            f.write("")


def write_bgp_controller_app():
    app_code = f"""\
from ryu.base import app_manager
from ryu.services.protocols.bgp.bgpspeaker import BGPSpeaker
from ryu.lib import hub


def best_path_change_handler(event):
    print("Best path changed:", event)


class Lab9RyuBGP(app_manager.RyuApp):
    def __init__(self, *args, **kwargs):
        super(Lab9RyuBGP, self).__init__(*args, **kwargs)

        self.speaker = BGPSpeaker(
            as_number={LOCAL_BGP_AS},
            router_id="{LOCAL_ROUTER_ID}",
            best_path_change_handler=best_path_change_handler
        )

        self.speaker.neighbor_add(
            "{PEER_IP}",
            {PEER_AS}
        )

        self.monitor_thread = hub.spawn(self._keepalive)

    def _keepalive(self):
        while True:
            hub.sleep(10)
"""
    app_path = os.path.join(CONTROLLER_APP_DIR, "lab9_ryu_bgp.py")
    with open(app_path, "w") as f:
        f.write(app_code)

    print("[OK] Wrote Ryu BGP app")
    return app_path


def remove_existing_ryu_container():
    try:
        container = docker_client.containers.get(SDN_CONTROLLER_CONTAINER)
        container.remove(force=True)
        print(f"[INFO] Removed existing container: {SDN_CONTROLLER_CONTAINER}")
    except docker.errors.NotFound:
        pass


def start_ryu_container():
    container = docker_client.containers.run(
        "osrg/ryu",
        name=SDN_CONTROLLER_CONTAINER,
        command='sh -c "cd /ryu-app && PYTHONPATH=/ryu-app nohup ryu-manager lab9_ryu_bgp >/tmp/ryu.log 2>&1 & tail -f /dev/null"',
        volumes={CONTROLLER_APP_DIR: {"bind": "/ryu-app", "mode": "rw"}},
        detach=True,
        tty=True,
        stdin_open=True,
    )
    print(f"[OK] Started Ryu container: {SDN_CONTROLLER_CONTAINER}")
    return container


def attach_ryu_to_bridge(container):
    bridge = docker_client.networks.get(BRIDGE_NAME)

    container.reload()
    networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
    if BRIDGE_NAME in networks:
        print(f"[INFO] Container already connected to {BRIDGE_NAME}")
        return

    bridge.connect(container, ipv4_address=SDN_CONTROLLER_IP)
    print(f"[OK] Connected {SDN_CONTROLLER_CONTAINER} to {BRIDGE_NAME} with IP {SDN_CONTROLLER_IP}")


def show_ryu_status():
    container = docker_client.containers.get(SDN_CONTROLLER_CONTAINER)
    container.reload()

    print("\n=== Ryu Container Status ===")
    print(f"[INFO] Name: {container.name}")
    print(f"[INFO] Status: {container.status}")

    networks = container.attrs.get("NetworkSettings", {}).get("Networks", {})
    if BRIDGE_NAME in networks:
        print(f"[INFO] IP on {BRIDGE_NAME}: {networks[BRIDGE_NAME].get('IPAddress')}")


def show_ryu_logs():
    container = docker_client.containers.get(SDN_CONTROLLER_CONTAINER)
    logs = container.logs(tail=50).decode(errors="ignore")

    print("\n=== Recent Ryu Logs ===")
    print(logs if logs.strip() else "[INFO] No logs yet")


def deploy_ryu_service():
    print("=== Ryu Automation ===")

    ensure_controller_app_dir()
    write_bgp_controller_app()
    remove_existing_ryu_container()
    container = start_ryu_container()
    time.sleep(3)
    attach_ryu_to_bridge(container)
    time.sleep(5)
    show_ryu_status()
    show_ryu_logs()

    print("[DONE] Ryu setup completed.")


if __name__ == "__main__":
    deploy_ryu_service()
import paramiko


def reboot_camera(cam, timeout=8):
    """Si collega via SSH alla camera (stesse credenziali già usate per FTP,
    come da configurazione yi-hack) ed esegue 'busybox reboot -f'.

    Non aspettiamo l'esito del comando: la camera si riavvia e la
    connessione cade quasi subito, è il comportamento atteso — quindi
    trattiamo eventuali eccezioni di chiusura connessione come normali,
    non come errori da segnalare all'utente.
    """
    host = cam["host"]
    port = cam.get("ssh_port", 22)
    user = cam.get("user")
    password = cam.get("password", "")

    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        client.connect(
            host,
            port=port,
            username=user,
            password=password,
            timeout=timeout,
            banner_timeout=timeout,
            auth_timeout=timeout,
            look_for_keys=False,
            allow_agent=False,
        )
        client.exec_command("busybox reboot -f", timeout=timeout)
    finally:
        try:
            client.close()
        except Exception:
            pass

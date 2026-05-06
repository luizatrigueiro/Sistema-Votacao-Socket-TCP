import socket
import threading
import json
import sys
import time

SERVER_HOST = "127.0.0.1"
SERVER_PORT = 9090

# Cores ANSI para terminal
RESET  = "\033[0m"
BOLD   = "\033[1m"
RED    = "\033[91m"
GREEN  = "\033[92m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
GRAY   = "\033[90m"
BLUE   = "\033[94m"
MAGENTA= "\033[95m"

voted = False
session_closed = False

# Função para gerar barra de progresso
def bar(count, total, width=24):
    if total == 0:
        filled = 0
    else:
        filled = int(count / total * width)
    return "█" * filled + "░" * (width - filled)

# Função para imprimir o placar de votação
def print_scoreboard(data):
    print(f"\n{CYAN}{'─'*52}{RESET}")
    print(f"{BOLD}{CYAN}  PLACAR ATUALIZADO{RESET}")
    print(f"  {data.get('title','')}")
    print(f"{CYAN}{'─'*52}{RESET}")

    scores = data.get("scores", {})
    total = data.get("total_votes", 0)
    cores = {"SIM": GREEN, "NAO": RED, "ABSTENCAO": YELLOW}

    for opcao, info in scores.items():
        votos = info["votos"]
        pct   = info["percentual"]
        cor   = cores.get(opcao, BLUE)
        barra = bar(votos, total)
        print(f"  {cor}{BOLD}{opcao:<12}{RESET} {barra}  {cor}{votos:>3} votos ({pct:.1f}%){RESET}")

    print(f"{CYAN}{'─'*52}{RESET}")
    print(f"  Total de votos: {BOLD}{total}{RESET}  |  Status: ", end="")

    status = data.get("status", "?")
    if status == "OPEN":
        print(f"{GREEN}ABERTA{RESET}")
    else:
        print(f"{RED}ENCERRADA{RESET}")
    print(f"{CYAN}{'─'*52}{RESET}")

# Thread que escuta mensagens do servidor continuamente
def receive_loop(sock):
    global voted, session_closed
    buffer = ""
    try:
        while True:
            data = sock.recv(4096)
            if not data:
                print(f"\n{RED}[DESCONECTADO] Servidor encerrou a conexão.{RESET}")
                break

            buffer += data.decode("utf-8")
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()
                if not line:
                    continue

                try:
                    msg = json.loads(line)
                except json.JSONDecodeError:
                    continue

                mtype = msg.get("type", "")

                if mtype == "WELCOME":
                    print(f"\n{CYAN}{'═'*52}{RESET}")
                    print(f"{BOLD}{CYAN}  SISTEMA DE VOTAÇÃO DIGITAL - EQUIPE 07{RESET}")
                    print(f"{CYAN}{'═'*52}{RESET}")
                    print(f"  {msg.get('message','')}")
                    print(f"  Pauta: {BOLD}{msg.get('title','')}{RESET}")
                    print(f"  Opções: {YELLOW}{', '.join(msg.get('options', []))}{RESET}")
                    print(f"  Status: {'Aberta' if msg.get('status')=='OPEN' else 'Encerrada'}")
                    print(f"\n{GRAY}  → {msg.get('protocol','')}{RESET}")
                    print(f"{CYAN}{'═'*52}{RESET}\n")

                elif mtype == "AUTH_OK":
                    print(f"\n{GREEN}{msg.get('message','')}{RESET}")
                    print(f"  Opções disponíveis: {YELLOW}{', '.join(msg.get('options',[]))}{RESET}")

                elif mtype == "ALREADY_VOTED":
                    voted = True
                    print(f"\n{YELLOW}{msg.get('message','')}{RESET}")

                elif mtype == "VOTE_ACCEPTED":
                    voted = True
                    print(f"\n{GREEN}{BOLD}{msg.get('message','')}{RESET}")

                elif mtype == "SCOREBOARD_UPDATE":
                    print_scoreboard(msg)
                    if msg.get("status") == "CLOSED":
                        session_closed = True

                elif mtype == "VOTE_CLOSED":
                    session_closed = True
                    print(f"\n{RED}{BOLD}{msg.get('message','')}{RESET}")

                elif mtype == "ERROR":
                    print(f"\n{RED}ERRO: {msg.get('message','')}{RESET}")

                else:
                    print(f"\n{GRAY}[{mtype}] {msg}{RESET}")

                print(f"{GRAY}> {RESET}", end="", flush=True)

    except Exception as e:
        if "9090" not in str(e):
            print(f"\n{RED}[ERRO RECEPÇÃO] {e}{RESET}")


def send_command(sock, command: str):
    sock.sendall((command.strip() + "\n").encode("utf-8"))

# Menu interativo para o usuário
def interactive_menu(sock):
    print(f"\n{GRAY}Comandos disponíveis:{RESET}")
    print(f"  {YELLOW}CONNECT|<TOKEN>{RESET}        → identificar-se")
    print(f"  {YELLOW}CAST_VOTE|SIM{RESET}           → votar SIM")
    print(f"  {YELLOW}CAST_VOTE|NAO{RESET}           → votar NÃO")
    print(f"  {YELLOW}CAST_VOTE|ABSTENCAO{RESET}     → votar ABSTENÇÃO")
    print(f"  {YELLOW}GET_STATUS{RESET}              → ver placar atual")
    print(f"  {YELLOW}CLOSE_VOTE{RESET}              → encerrar votação (admin)")
    print(f"  {YELLOW}sair{RESET}                    → desconectar")
    print()

    while True:
        try:
            cmd = input(f"{GRAY}> {RESET}").strip()
        except (EOFError, KeyboardInterrupt):
            print(f"\n{YELLOW}Desconectando...{RESET}")
            break

        if not cmd:
            continue

        if cmd.lower() in ("sair", "exit", "quit"):
            print(f"{YELLOW}Encerrando cliente.{RESET}")
            break

        send_command(sock, cmd)
        time.sleep(0.1) 


def main():
    global SERVER_HOST, SERVER_PORT

    # Suporte a argumentos: python client.py [HOST] [PORT]
    if len(sys.argv) >= 2:
        SERVER_HOST = sys.argv[1]
    if len(sys.argv) >= 3:
        SERVER_PORT = int(sys.argv[2])

    print(f"{CYAN}Conectando a {SERVER_HOST}:{SERVER_PORT}...{RESET}")

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.connect((SERVER_HOST, SERVER_PORT))
    except ConnectionRefusedError:
        print(f"{RED}✗ Não foi possível conectar ao servidor {SERVER_HOST}:{SERVER_PORT}{RESET}")
        print(f"  Certifique-se de que o servidor está rodando: {YELLOW}python voting_server.py{RESET}")
        sys.exit(1)

    # Thread de recepção em background
    t = threading.Thread(target=receive_loop, args=(sock,), daemon=True)
    t.start()

    time.sleep(0.3) 
    interactive_menu(sock)

    sock.close()


if __name__ == "__main__":
    main()

import socket
import threading
import json
import time
import signal
import sys
import select
from datetime import datetime

HOST = "0.0.0.0"
PORT = 9090
MAX_CLIENTS = 50

lock = threading.Lock()
server_stop = threading.Event()

voting_session = {
    "title": "Sistema de Votação de Assembleia Digital",
    "options": {
        "SIM": 0,
        "NAO": 0,
        "ABSTENCAO": 0
    },
    "status": "OPEN",          
    "start_time": datetime.now().isoformat(),
    "end_time": None
}

voted_tokens = {}       
connected_clients = {}  


def signal_handler(sig, frame):
    print("\n[SERVIDOR] Encerrando...")
    server_stop.set()
    sys.exit(0)

# Função para construir mensagens JSON
def build_response(msg_type: str, payload: dict) -> bytes:
    msg = json.dumps({"type": msg_type, **payload}) + "\n"
    return msg.encode("utf-8")

# Função para enviar dados com segurança
def send_safe(conn: socket.socket, data: bytes) -> bool:
    if conn is None:
        return False
    
    total_sent = 0
    data_len = len(data)
    
    while total_sent < data_len:
        sent = conn.send(data[total_sent:])
        if sent == 0:
            return False
        total_sent += sent
    
    return True

# Função para fechar conexão com segurança
def close_safe(conn: socket.socket):
    if conn is None:
        return
    
    if conn.fileno() != -1:
        conn.shutdown(socket.SHUT_RDWR)
    conn.close()


# Teste de carga: simula múltiplos clientes votando simultaneamente
def parse_message(raw: str):
    parts = raw.strip().split("|")
    command = parts[0].upper()
    args = parts[1:] if len(parts) > 1 else []
    return command, args

# Função para gerar barra de progresso
def scoreboard_snapshot():
    total = sum(voting_session["options"].values())
    scores = {}
    for opt, count in voting_session["options"].items():
        pct = round((count / total * 100), 1) if total > 0 else 0
        scores[opt] = {"votos": count, "percentual": pct}
    return {
        "title": voting_session["title"],
        "scores": scores,
        "total_votes": total,
        "total_participants": len(voted_tokens),
        "status": voting_session["status"],
        "timestamp": datetime.now().isoformat()
    }


# Função para enviar o placar atualizado a TODOS os clientes conectados
def broadcast_scoreboard():
    with lock:
        snap = scoreboard_snapshot()
        payload = build_response("SCOREBOARD_UPDATE", snap)
        dead = []
        
        for conn in list(connected_clients.keys()):
            if not send_safe(conn, payload):
                dead.append(conn)
        
        for conn in dead:
            remove_client(conn)

    print(f"[BROADCAST] Placar enviado para {len(connected_clients)} cliente(s).")


# Função para enviar mensagens de broadcast (ex: encerramento)
def broadcast_message(msg_type: str, text: str):
    payload = build_response(msg_type, {"message": text, "timestamp": datetime.now().isoformat()})
    with lock:
        dead = []
        
        for conn in list(connected_clients.keys()):
            if not send_safe(conn, payload):
                dead.append(conn)
        
        for conn in dead:
            remove_client(conn)

# Função para remover cliente da lista e fechar conexão
def remove_client(conn: socket.socket):
    if conn not in connected_clients:
        return
    
    info = connected_clients.pop(conn, None)
    
    if conn.fileno() != -1:
        close_safe(conn)
    
    if info:
        print(f"[DESCONEXÃO] Token={info.get('token','?')} | {info.get('addr','?')}")

# Thread que lida com cada cliente conectado
def handle_client(conn: socket.socket, addr: tuple):
    token = None
    print(f"\n[CONEXÃO] Novo cliente: {addr}")

    welcome = build_response("WELCOME", {
        "message": "Bem-vindo ao Sistema de Votação Digital - Equipe 07",
        "protocol": "Use: CONNECT|<TOKEN>  depois  CAST_VOTE|<OPCAO>",
        "options": list(voting_session["options"].keys()),
        "title": voting_session["title"],
        "status": voting_session["status"]
    })
    
    if not send_safe(conn, welcome):
        with lock:
            remove_client(conn)
        print(f"[ENCERRADO] Conexão com {addr} finalizada (falha no envio).")
        return

    buffer = ""
    connection_active = True

    while connection_active:
        data = b""
        
        if conn.fileno() == -1:
            connection_active = False
            break
        
        data = conn.recv(1024)
        
        if not data or len(data) == 0:
            connection_active = False
            break

        buffer += data.decode("utf-8", errors="ignore")
        
        while "\n" in buffer and connection_active:
            line, buffer = buffer.split("\n", 1)
            line = line.strip()
            
            if not line:
                continue

            command, args = parse_message(line)
            print(f"[MSG] {addr} → '{line}'")

            if command == "CONNECT":
                if not args:
                    send_safe(conn, build_response("ERROR", {"message": "Token ausente. Use: CONNECT|<TOKEN>"}))
                    continue

                token = args[0].upper().strip()
                with lock:
                    if conn in connected_clients:
                        connected_clients[conn]["token"] = token

                if token in voted_tokens:
                    send_safe(conn, build_response("ALREADY_VOTED", {
                        "message": f"Token {token} já registrou voto: {voted_tokens[token]}",
                        "your_vote": voted_tokens[token]
                    }))
                else:
                    send_safe(conn, build_response("AUTH_OK", {
                        "message": f"Identificado como {token}. Aguardando seu voto.",
                        "options": list(voting_session["options"].keys())
                    }))

                with lock:
                    snap = scoreboard_snapshot()
                send_safe(conn, build_response("SCOREBOARD_UPDATE", snap))

            elif command == "CAST_VOTE":
                if not token:
                    send_safe(conn, build_response("ERROR", {"message": "Identifique-se primeiro com CONNECT|<TOKEN>"}))
                    continue

                if not args:
                    send_safe(conn, build_response("ERROR", {"message": "Informe a opção. Use: CAST_VOTE|SIM  ou  CAST_VOTE|NAO  ou  CAST_VOTE|ABSTENCAO"}))
                    continue

                opcao = args[0].upper().strip()

                with lock:
                    if voting_session["status"] == "CLOSED":
                        send_safe(conn, build_response("ERROR", {"message": "Votação encerrada. Não é possível registrar novos votos."}))
                        continue

                    if opcao not in voting_session["options"]:
                        send_safe(conn, build_response("ERROR", {
                            "message": f"Opção inválida: '{opcao}'. Opções disponíveis: {list(voting_session['options'].keys())}"
                        }))
                        continue

                    if token in voted_tokens:
                        send_safe(conn, build_response("ALREADY_VOTED", {
                            "message": f"Token {token} já votou em: {voted_tokens[token]}",
                            "your_vote": voted_tokens[token]
                        }))
                        continue

                    voted_tokens[token] = opcao
                    voting_session["options"][opcao] += 1
                    total = sum(voting_session["options"].values())

                send_safe(conn, build_response("VOTE_ACCEPTED", {
                    "message": f"Voto '{opcao}' registrado com sucesso para o token {token}.",
                    "token": token,
                    "option": opcao,
                    "total_votes": total
                }))

                print(f"[VOTO] Token={token} | Opção={opcao} | Total={total}")
                broadcast_scoreboard()

            elif command == "GET_STATUS":
                with lock:
                    snap = scoreboard_snapshot()
                send_safe(conn, build_response("SCOREBOARD_UPDATE", snap))

            elif command == "CLOSE_VOTE":
                with lock:
                    if voting_session["status"] == "CLOSED":
                        send_safe(conn, build_response("ERROR", {"message": "Votação já encerrada."}))
                        continue
                    
                    voting_session["status"] = "CLOSED"
                    voting_session["end_time"] = datetime.now().isoformat()
                    snap = scoreboard_snapshot()

                print(f"\n[ADMIN] Votação encerrada por {token or addr}")
                send_safe(conn, build_response("VOTE_CLOSED", {"message": "Votação encerrada com sucesso!"}))
                broadcast_message("VOTE_CLOSED", "A votação foi encerrada pelo administrador.")
                broadcast_scoreboard()

            else:
                send_safe(conn, build_response("ERROR", {
                    "message": f"Comando desconhecido: '{command}'. Comandos válidos: CONNECT, CAST_VOTE, GET_STATUS, CLOSE_VOTE"
                }))

    with lock:
        remove_client(conn)
    print(f"[ENCERRADO] Conexão com {addr} finalizada.")

# Início do servidor
def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(MAX_CLIENTS)

    print("=" * 60)
    print("  SISTEMA DE VOTAÇÃO - EQUIPE 07 | Sistemas Distribuídos")
    print("=" * 60)
    print(f"  Servidor TCP ouvindo em {HOST}:{PORT}")
    print(f"  Pauta: {voting_session['title']}")
    print(f"  Opções: {list(voting_session['options'].keys())}")
    print("=" * 60)
    print("  Aguardando conexões...\n")

    while not server_stop.is_set():
        ready = select.select([server], [], [], 1.0)
        
        if ready[0]:
            conn, addr = server.accept()
            
            if conn and addr and not server_stop.is_set():
                with lock:
                    connected_clients[conn] = {"token": None, "addr": addr}
                t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
                t.start()

    server.close()


if __name__ == "__main__":
    signal.signal(signal.SIGINT, signal_handler)
    start_server()

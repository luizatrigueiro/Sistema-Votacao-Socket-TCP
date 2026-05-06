# Sistema de Votação de Assembleia Digital (Socket TCP)

Sistema distribuído cliente-servidor usando Socket TCP para conduzir votações de assembleia (condomínio, empresa, etc.) com múltiplos clientes conectados simultaneamente.

## Proposta Atendida

Este projeto implementa a proposta de:

- servidor TCP central para gerenciar sessão de votação;
- clientes TCP concorrentes para participação em tempo real;
- identificação de cada participante por Token;
- validação de voto único por Token;
- comando de voto no formato CAST_VOTE|opcao;
- broadcast do placar atualizado para todos os clientes conectados após cada voto.

## Arquitetura

- server.py: mantém estado global da votação, valida comandos e distribui atualizações.
- client.py: interface de terminal para autenticação por Token, envio de comandos e visualização do placar em tempo real.

### Comunicação

- Transporte: TCP.
- Formato de mensagens do servidor: JSON por linha (newline-delimited JSON).
- Formato de comandos do cliente: texto simples no padrão COMANDO|ARG1.

## Regras de Negócio

- Opções válidas de voto: SIM, NAO, ABSTENCAO.
- Cada Token pode registrar apenas 1 voto.
- Se Token já votou, o servidor responde ALREADY_VOTED e não contabiliza novo voto.
- Votação pode ser encerrada via CLOSE_VOTE.
- Após encerramento, novos votos são rejeitados.

## Protocolo de Comandos (Cliente -> Servidor)

- CONNECT|TOKEN
- CAST_VOTE|SIM
- CAST_VOTE|NAO
- CAST_VOTE|ABSTENCAO
- GET_STATUS
- CLOSE_VOTE

## Tipos de Resposta (Servidor -> Cliente)

- WELCOME
- AUTH_OK
- ALREADY_VOTED
- VOTE_ACCEPTED
- SCOREBOARD_UPDATE
- VOTE_CLOSED
- ERROR

## Concorrência e Consistência

- O servidor cria uma thread por cliente conectado.
- Estruturas compartilhadas (sessão, tokens e conexões) são protegidas por lock.
- O placar é enviado por broadcast a todos os sockets ativos após cada voto.

## Como Executar

Pré-requisitos:

- Python 3.10+.
- Ambiente de terminal (Windows PowerShell, CMD, Bash, etc.).

1. Clonar o repositório:

```bash
git clone https://github.com/luizatrigueiro/Sistema-Votacao-Socket-TCP.git
cd Sistema-Votacao-Socket-TCP
```

2. Iniciar o servidor:

```bash
python server.py
```

3. Em outro terminal, iniciar um cliente:

```bash
python client.py
```

4. Para múltiplos participantes, abrir mais terminais e repetir o passo do cliente.

## Exemplo de Uso

No cliente:

```text
CONNECT|MORADOR_001
CAST_VOTE|SIM
GET_STATUS
```

Outro cliente:

```text
CONNECT|MORADOR_002
CAST_VOTE|NAO
```

Ao receber cada voto, todos os clientes conectados recebem SCOREBOARD_UPDATE automaticamente.

## Cenários Validados

- múltiplos clientes conectados simultaneamente;
- voto único por Token;
- rejeição de voto duplicado;
- atualização parcial do placar em tempo real;
- encerramento da votação e bloqueio de novos votos.

## Estrutura do Projeto

```text
.
├── server.py
├── client.py
├── README.md
└── LICENSE
```

## Melhorias Futuras

- autenticação de administrador para CLOSE_VOTE;
- persistência de resultados em banco de dados;
- histórico de sessões de votação;
- suporte a TLS para criptografia de transporte;
- suíte de testes automatizados (integração/concorrência).
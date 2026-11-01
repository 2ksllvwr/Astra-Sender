# Astra Sender

![Windows](https://img.shields.io/badge/Windows-10%20%7C%2011-blue) ![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white) ![Versão](https://img.shields.io/badge/Versão-0.2.4-1477eb)

Automação de mensagens para Windows com uma interface compacta e direta. Configure perfis para diferentes aplicativos, selecione o campo de texto e o botão de envio na tela e faça envios imediatos ou agendados.

> **Estado:** versão beta, com correções de persistência e do `QDateTime`. A interface e o envio em aplicativos reais dependem de validação no Windows. Um clique registrado não garante a entrega da mensagem.

## Interface

As imagens abaixo são **ilustrações da interface da versão 0.2.4** com dados fictícios, não capturas de uma execução real. A interface foi construída com quatro abas no topo, sem menu lateral e sem subtítulo.

**Enviar** — escolha o perfil, escreva a mensagem, salve ou envie. Use o botão ⌖ para marcar os pontos da tela.

![Astra Sender - Enviar](docs/imagens/enviar.svg)

**Agendamentos** — crie, edite, pause, retome ou exclua tarefas. O formulário abre em uma pequena janela.

![Astra Sender - Agendamentos](docs/imagens/agendamentos.svg)

**Histórico** — veja os registros de execução e falhas.

![Astra Sender - Histórico](docs/imagens/historico.svg)

**Perfis** — cadastre aplicativos e selecione seus pontos de digitação e envio.

![Astra Sender - Perfis](docs/imagens/perfis.svg)

## Funcionalidades

- Perfis independentes para mensageiros desktop e páginas no navegador, com configurações armazenadas em SQLite.
- Seletor visual para marcar as coordenadas do campo de mensagem e do botão de enviar.
- Modos **Escrever e enviar** ou **Somente enviar**.
- Agendamentos únicos, diários e semanais, com edição, pausa e exclusão.
- Histórico de tentativas, erros e ações executadas; **não confirma entrega**.
- Minimização para a bandeja do Windows, quando disponível. O programa precisa continuar em execução para processar os horários.
- Automação por acessibilidade do Windows (UI Automation) quando compatível e alternativa por mouse, mediante autorização do perfil.

## Como usar

1. Na aba **Perfis**, escolha **+ Novo** e cadastre o aplicativo. Um perfil pode ser salvo antes de configurar os pontos.
2. Com o aplicativo de mensagens aberto, selecione o perfil e use **Marcar campo** e **Marcar envio**. Também é possível usar o botão ⌖ na aba **Enviar**.
3. Em **Enviar**, escreva a mensagem e clique em **Salvar Mensagem**, **Enviar Agora** ou **Agendar...**.
4. Em **Agendamentos**, acompanhe tarefas, crie novas e gerencie as existentes.
5. Em **Histórico**, examine os resultados de cada tentativa.

### Limitações

O envio por coordenadas exige que a janela e os botões estejam nas posições configuradas e pode assumir o controle do mouse/teclado momentaneamente. O modo UI Automation depende dos controles de acessibilidade expostos pelo aplicativo e pode falhar. O programa não garante automação em janelas minimizadas, com a tela bloqueada ou quando o computador estiver desligado. Use apenas para mensagens autorizadas e conforme as regras das plataformas.

## Baixar, compilar e publicar

Quando houver uma compilação publicada, consulte [Releases](https://github.com/2ksllvwr/Astra-Sender/releases) ou [Actions → Artifacts](https://github.com/2ksllvwr/Astra-Sender/actions). O repositório precisa estar criado e configurado antes que esses links forneçam arquivos.

Para compilar localmente, extraia o projeto no Windows e execute **`COMPILAR_WINDOWS.bat`**. Alternativamente:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_windows.ps1
```

O executável local estará em `dist\AstraSender\AstraSender.exe` após uma compilação bem-sucedida. O workflow `.github/workflows/windows-build.yml` testa o código e compila automaticamente ao enviar alterações para a branch principal; cada compilação aprovada da branch principal publica uma pré-versão em Releases com o executável, ZIP portátil e SHA256. Tags `v*` também publicam versões identificadas. Não é necessário compilar no seu computador.

Scripts opcionais: `INICIAR_GITHUB.bat` para configuração inicial com sua autorização, `PUBLICAR_ATUALIZACAO.bat` para enviar modificações e `PUBLICAR_VERSAO.bat` para criar uma versão.

## Dados e migração

Perfis e agendamentos ficam no arquivo `%LOCALAPPDATA%\AstraSender\astra_sender.db`, fora do diretório da aplicação. Na primeira execução, se o banco novo ainda não existir, o sistema tenta copiar o banco antigo de `%LOCALAPPDATA%\PySender\pysender.db`, sem apagar o original. Recomenda-se fazer backup antes da atualização.

## Estrutura

```text
Astra-Sender/
├── app/
│   ├── automation/         # UI Automation e coordenadas
│   ├── database/           # Persistência e migração SQLite
│   └── ui/                 # Interface com quatro abas e seletor
├── docs/imagens/           # Ilustrações das quatro abas
├── tests/                  # Testes automatizados
├── .github/workflows/      # Build automático para Windows
├── main.py
├── COMPILAR_WINDOWS.bat
└── requirements.txt
```

Este projeto não é afiliado ao WhatsApp, Discord, Telegram ou aos desenvolvedores dessas plataformas.

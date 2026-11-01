<div align="center">

# Astra Sender

**Suas mensagens. No horário certo.**

Automação de mensagens para Windows, com perfis independentes,<br>
agendamentos e uma interface que mantém tudo ao alcance.

![Windows](https://img.shields.io/badge/Windows-10%20%2F%2011-1477EB?style=flat-square)
![Versão](https://img.shields.io/badge/versão-0.2.4%20beta-24374D?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.11%2B-24374D?style=flat-square)

**[Baixar para Windows](https://github.com/2ksllvwr/Astra-Sender/releases)** · **[Primeiros passos](#primeiros-passos)** · **[Desenvolvimento](docs/desenvolvimento.md)**

<br>

<img src="docs/imagens/enviar.svg" alt="Aba Enviar do Astra Sender: perfil, mensagem e controles de envio" width="900">

<sub>Ilustração da interface 0.2.4. Os dados apresentados são exemplos.</sub>

</div>

<br>

## Uma rotina, vários destinos

Crie um perfil para cada aplicativo, marque onde escrever e onde enviar. Depois, use a mesma configuração para uma mensagem imediata ou uma tarefa agendada.

| Organize | Programe | Acompanhe |
| :--- | :--- | :--- |
| Perfis com aplicativo, mensagem e pontos de interação próprios. | Execuções únicas, diárias ou semanais, com opção de pausar e retomar. | Histórico das ações executadas e dos erros encontrados. |

## Baixar e usar

Abra **[Releases](https://github.com/2ksllvwr/Astra-Sender/releases)** e escolha a compilação mais recente que tenha arquivos disponíveis.

| Arquivo | Como usar |
| :--- | :--- |
| **`AstraSender.exe`** | Baixe e execute. Não precisa instalar Python. |
| `AstraSender-versao-em-pasta.zip` | Extraia todo o conteúdo e abra `AstraSender.exe`, mantendo os arquivos juntos. |
| `SHA256SUMS.txt` | Consulte os hashes para conferir a integridade do download. |

As compilações da branch principal são identificadas como **pré-versões**. Como o repositório é privado, entre na conta com acesso para visualizar os downloads.

## Primeiros passos

1. **Crie um perfil.** Em **Perfis → + Novo**, dê um nome ao destino e indique o aplicativo.
2. **Marque os pontos.** Com a janela de destino aberta, use **Marcar campo** e **Marcar envio**.
3. **Prepare a mensagem.** Na aba **Enviar**, selecione o perfil e escreva o texto. Use **Salvar Mensagem** para reutilizá-lo.
4. **Escolha quando enviar.** Clique em **Enviar Agora** ou em **Agendar…**, definindo a data, o horário e a repetição.
5. **Confira a execução.** Consulte **Histórico** para verificar as ações registradas ou identificar falhas.

> Deixe o Astra Sender em execução para processar os agendamentos. Quando a bandeja do Windows estiver disponível, o aplicativo pode permanecer minimizado nela.

## Quatro abas, uma interface direta

### Enviar

O perfil, a mensagem e os controles principais ficam na mesma tela. Escolha entre **Escrever e enviar** ou **Somente enviar**, quando o texto já estiver preparado no aplicativo de destino.

### Agendamentos

Veja as tarefas em uma lista e abra o formulário para ajustar horários e recorrência. Pause, retome ou exclua uma tarefa conforme sua rotina.

<img src="docs/imagens/agendamentos.svg" alt="Ilustração da aba Agendamentos" width="900">

<details>
<summary><strong>Conheça as abas Perfis e Histórico</strong></summary>

### Perfis

Mantenha configurações separadas para cada destino, incluindo pontos de interação e método de automação.

<img src="docs/imagens/perfis.svg" alt="Ilustração da aba Perfis" width="900">

### Histórico

Consulte a data, o perfil utilizado e o resultado de cada tentativa. Uma ação executada registra a interação feita pelo programa; não confirma o recebimento da mensagem.

<img src="docs/imagens/historico.svg" alt="Ilustração da aba Histórico" width="900">

</details>

<sub>As imagens desta página são ilustrações do programa, não capturas de testes em aplicativos externos.</sub>

## Atualizações sem compilação manual

Cada atualização enviada à `main` aciona o **GitHub Actions**. O processo executa os testes no Windows, gera as duas distribuições e publica os arquivos em Releases somente após uma compilação bem-sucedida.

**[Acompanhar compilações](https://github.com/2ksllvwr/Astra-Sender/actions)** · **[Ver versões disponíveis](https://github.com/2ksllvwr/Astra-Sender/releases)**

Para atualizar, feche o programa e substitua o executável ou a pasta da aplicação pela nova versão. O download e a instalação ainda são manuais; a geração dos arquivos é automática.

## Seus dados continuam com você

Perfis, mensagens salvas, tarefas e histórico são armazenados localmente em SQLite, fora da pasta do executável:

```text
%LOCALAPPDATA%\AstraSender\astra_sender.db
```

Na primeira execução, o Astra Sender tenta importar o banco antigo do PySender, quando disponível, sem apagar o original. Faça uma cópia do banco com o aplicativo fechado antes de atualizar.

## Antes de agendar

- A automação funciona no Windows e depende dos controles disponíveis no aplicativo de destino.
- No modo por coordenadas, mantenha a janela na posição marcada. O programa poderá utilizar o mouse e o teclado durante a execução.
- A tela bloqueada, o computador desligado ou uma janela minimizada podem impedir a tarefa.
- A versão está em **beta**. Valide o envio com um destino de teste antes de usá-la na sua rotina.

---

<div align="center">

**Astra Sender**<br>
<sub>Projeto independente. Sem afiliação com WhatsApp, Discord, Telegram ou seus desenvolvedores.</sub>

</div>

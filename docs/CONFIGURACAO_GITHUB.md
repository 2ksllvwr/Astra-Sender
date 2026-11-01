# Publicar o Astra Sender sem compilar no próprio Windows

## Primeiro acesso (uma vez)

1. Extraia o ZIP e abra a pasta **Astra-Sender**.
2. Dê dois cliques no arquivo **`INICIAR_GITHUB.bat`**.
3. Caso o Git e o GitHub CLI não estejam instalados, o script solicitará sua instalação pelo **winget** (quando disponível).
4. Na primeira vez, faça login no seu GitHub **pela janela do navegador que será aberta pelo GitHub CLI**. Não envie senha nem token ao ChatGPT.
5. O script confirmará que a conta conectada é **2ksllvwr**, inicializará o Git local, criará o repositório **privado** `2ksllvwr/Astra-Sender` se não existir e enviará o código.
6. O GitHub Actions compilará automaticamente na branch principal. O script tentará criar a tag experimental `v0.2.4-beta.1`, que também produzirá uma Release.

Para acompanhar: <https://github.com/2ksllvwr/Astra-Sender/actions>

Para baixar as versões: <https://github.com/2ksllvwr/Astra-Sender/releases>

> O script não utiliza tokens gravados no projeto. O login é feito pelo GitHub CLI e exige sua autorização. Para publicar o repositório ao público, mude manualmente a visibilidade no GitHub após analisar o código e os arquivos.

## Próximas atualizações

- **`PUBLICAR_ATUALIZACAO.bat`:** envia alterações à `main` e inicia uma compilação. Resultado em **Actions > Artifacts**.
- **`PUBLICAR_VERSAO.bat`:** solicita número da tag (`v0.2.4-beta.1`, por exemplo) e inicia uma compilação com publicação de nova **Release**.

Não edite nem publique seu banco `%LOCALAPPDATA%\AstraSender\astra_sender.db` no GitHub. O `.gitignore` bloqueia extensões comuns de banco, além de ambientes e artefatos locais.

## Limitações

- Scripts `.bat` e `.ps1` foram preparados, mas **não foram executados no Windows deste ambiente**.
- Dependem de GitHub CLI, Git e internet; a instalação automática depende do `winget`.
- Seu GitHub precisa permitir **Actions** e fornecer a cota correspondente, inclusive em repositórios privados.
- Se o repositório já existir com histórico divergente, o push falhará sem forçar sobrescrita.
- `AstraSender.exe` gerado não garante que a automação funcione em todas as janelas; teste manualmente.

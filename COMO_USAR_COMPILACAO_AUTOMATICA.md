# Aplicativo automático a cada atualização

Depois de configurar o repositório, cada atualização enviada para `main` dispara o GitHub Actions no Windows. Ele executa os testes, compila e publica uma pré-versão em **Releases** com:

- `AstraSender.exe`: executável único.
- `AstraSender-versao-em-pasta.zip`: versão portátil em pasta.
- `SHA256SUMS.txt`: hashes dos arquivos.

Abra a seção **Releases** e baixe a compilação mais recente bem-sucedida. A pré-versão usa o identificador `build-N-T` (execução e tentativa), mantendo as anteriores disponíveis. Falhas de testes ou compilação impedem a publicação.

Você só precisa baixar e abrir o programa; Python e compilação manual não são necessários no computador que vai usá-lo. Isso automatiza a geração do aplicativo, não a instalação de atualizações dentro do programa.

Tags `v*` continuam disponíveis para versões nomeadas. A aba **Actions** mostra o andamento, os logs e os arquivos de cada execução. Em repositório privado é necessário entrar na conta autorizada para baixar os arquivos.

# Desenvolvimento

## Ambiente local

Use Python 3.11 ou superior no Windows. Na raiz do projeto:

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python main.py
```

## Validação

```powershell
.venv\Scripts\python -m compileall -q main.py app tests
.venv\Scripts\python -m unittest discover -s tests -v
```

A suíte cobre persistência, migração do banco legado e abertura da interface. A interação com aplicativos externos requer testes manuais no Windows.

## Publicação

O workflow `.github/workflows/windows-build.yml` executa os testes e o PyInstaller em um runner Windows. Um push em `main` publica uma pré-versão `build-N-T`, com o número da execução e da tentativa. Tags `v*` publicam versões nomeadas. A execução manual também está disponível em Actions.

São gerados um executável único, um ZIP portátil e hashes SHA256. Uma falha impede a publicação. O job de publicação recebe `contents: write`; o job de compilação utiliza somente leitura do repositório.

## Organização

| Caminho | Responsabilidade |
| --- | --- |
| `app/ui/` | Interface e seleção visual de coordenadas. |
| `app/automation/` | Interações por UI Automation e mouse. |
| `app/database/` | SQLite, persistência e migrações. |
| `tests/` | Testes automatizados. |
| `docs/imagens/` | Ilustrações usadas no README. |
| `.github/workflows/` | Compilação e publicação. |

Dados locais e ambientes virtuais são excluídos pelo `.gitignore`. Não adicione bancos de usuários ou credenciais ao código-fonte.

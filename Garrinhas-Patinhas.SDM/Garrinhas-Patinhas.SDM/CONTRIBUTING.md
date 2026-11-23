# Como colaborar

1. Pegue uma **issue** do quadro (Projects) e se atribua a ela.
2. Crie a branch a partir da `develop`: `git checkout -b feature/nome-curto`.
3. Faça commits pequenos no padrão **Conventional Commits**: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
4. Abra um **Pull Request** para a `develop` referenciando a issue (`Closes #12`). Peça revisão de um colega.
5. Após aprovado, faça o merge. A `main` só recebe merge da `develop` nas entregas (use *tags*: `v1.0-milestone1` … `v1.0`).

**Nunca** suba `.env`, senhas, tokens ou arquivos `.db`.

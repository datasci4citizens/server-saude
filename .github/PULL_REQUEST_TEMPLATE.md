## Tipo de mudança

Selecione o tipo com um `x`:

- [ ] **feat**: Nova funcionalidade
- [ ] **fix**: Correção de bug
- [ ] **chore**: Tarefa de manutenção (ex: CI, dependências)
- [ ] **docs**: Documentação
- [ ] **refactor**: Mudança interna que não altera comportamento
- [ ] **test**: Adição ou correção de testes

## Escopo

Descreva o *escopo* (módulo, feature ou ticket)

## Título da PR (será o commit se usar squash!)

**Use o padrão Conventional Commit:**

```
<tipo>(<escopo>): <mensagem breve no imperativo>
```


**Exemplos válidos:**

- `feat(sau-24): adiciona endpoint de login mágico`
- `fix(nojira): corrige falha na autenticação`
- `chore(ci): atualiza versão do docker build-push`

## Checklist

- [ ] O título da PR segue o padrão Conventional Commits
- [ ] Foram feitos testes (ou não se aplica)
- [ ] O `CHANGELOG.md` será gerado automaticamente, não edite manualmente

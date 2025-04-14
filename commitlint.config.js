module.exports = {
    extends: ['@commitlint/config-conventional'],
    rules: {
      'type-enum': [
        2,
        'always',
        ['feat', 'fix', 'chore', 'docs', 'style', 'refactor', 'test', 'perf']
      ],
      'scope-empty': [2, 'never'],
      'scope-pattern': [2, 'always', '^SAU-[0-9]+$'],
      'subject-empty': [2, 'never'],
      'subject-case': [0],
      'header-pattern': [2, 'always', /^(\w+)\((SAU-\d+)\): (.+)$/],
    },
  };

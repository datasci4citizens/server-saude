module.exports = {
  extends: ['@commitlint/config-conventional'],
  rules: {
    'type-enum': [
      2,
      'always',
      ['feat', 'fix', 'chore', 'docs', 'style', 'refactor', 'test', 'perf']
    ],
    'scope-empty': [2, 'never'],
    'scope-case': [0],
    'subject-empty': [2, 'never'],
    'subject-case': [0],
  },
};

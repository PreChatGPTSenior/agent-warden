import js from '@eslint/js';
import { defineConfig } from 'eslint/config';
import globals from 'globals';
import tseslint from 'typescript-eslint';
import reactHooks from 'eslint-plugin-react-hooks';

export default defineConfig({
  files: ['**/*.{js,jsx,ts,tsx}'],
  extends: [js.configs.recommended, tseslint.configs.recommended],
  languageOptions: {
    globals: globals.browser,
    parserOptions: { ecmaFeatures: { jsx: true } },
  },
  linterOptions: { noInlineConfig: true, reportUnusedDisableDirectives: 'error' },
  plugins: { 'react-hooks': reactHooks },
  rules: {
    ...reactHooks.configs.recommended.rules,
    'react-hooks/exhaustive-deps': 'error',
  },
}, {
  files: ['**/*.tsx'],
  ignores: ['**/*.test.tsx', '**/*.spec.tsx'],
  rules: {
    'no-restricted-imports': ['error', {
      patterns: [{ group: ['**/mocks/**'], message: 'Components use API boundaries, not mock datasets.' }],
    }],
  },
});

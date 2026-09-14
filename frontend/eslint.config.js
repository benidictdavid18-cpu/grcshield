import js from '@eslint/js'
import reactHooks from 'eslint-plugin-react-hooks'
import tseslint from 'typescript-eslint'

// Deliberately small: the recommended sets plus the two hooks rules. A lint rule that
// fires on style nobody agreed to is a rule people learn to silence.
export default tseslint.config(
  { ignores: ['dist/', 'node_modules/', 'vite.config.ts'] },
  js.configs.recommended,
  ...tseslint.configs.recommended,
  {
    files: ['src/**/*.{ts,tsx}'],
    plugins: { 'react-hooks': reactHooks },
    rules: {
      ...reactHooks.configs.recommended.rules,
      // `_` prefixed unused arguments are how a callback declares it ignores a value.
      '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    },
  },
)

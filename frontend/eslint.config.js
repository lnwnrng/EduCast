import js from '@eslint/js'
import globals from 'globals'
import reactHooks from 'eslint-plugin-react-hooks'
import reactRefresh from 'eslint-plugin-react-refresh'
import tseslint from 'typescript-eslint'
import { defineConfig, globalIgnores } from 'eslint/config'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      js.configs.recommended,
      tseslint.configs.recommended,
      reactHooks.configs.flat.recommended,
      reactRefresh.configs.vite,
    ],
    languageOptions: {
      globals: globals.browser,
    },
    rules: {
      // 经典 React 数据获取模式（在 useEffect 中 fetch 并同步 setState 显示
      // 加载态）会触发该 React Compiler 实验规则；本项目未启用 React Compiler，
      // 该模式是有意为之，关闭以免误报。
      'react-hooks/set-state-in-effect': 'off',
    },
  },
])

import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
  {
    rules: {
      // Client pages fetch from FastAPI on mount and hydrate UTC clocks after
      // prerender. That pattern uses setState from effects; the React Compiler
      // lint rule is aimed at derived-state anti-patterns, not API loads.
      "react-hooks/set-state-in-effect": "off",
    },
  },
]);

export default eslintConfig;

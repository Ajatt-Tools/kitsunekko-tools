// Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { defineConfig } from "vitest/config";

export default defineConfig({
    test: {
        environment: "jsdom",
        include: ["tests/**/*.test.ts"],
        setupFiles: ["tests/setup.ts"],
        coverage: {
            provider: "v8",
            include: ["resources/site.js"],
            reporter: ["text"],
        },
    },
});

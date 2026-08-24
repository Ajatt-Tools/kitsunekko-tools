// Copyright: Ajatt-Tools and contributors; https://github.com/Ajatt-Tools
// License: GNU AGPL, version 3 or later; http://www.gnu.org/licenses/agpl.html

import { afterEach, beforeEach, vi } from "vitest";

/** Enable deterministic timers before each catalog JavaScript test. */
function enableFakeTimers(): void {
    vi.useFakeTimers();
}

/** Restore timer and mock state after each catalog JavaScript test. */
function restoreTestEnvironment(): void {
    vi.useRealTimers();
    vi.restoreAllMocks();
}

beforeEach(enableFakeTimers);
afterEach(restoreTestEnvironment);

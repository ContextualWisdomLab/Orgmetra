/** Run the dependency-free Orgmetra foundation validator. */

import { resolve } from 'node:path';
import { runCli } from './foundation-contract-core.mjs';

process.exitCode = runCli(process.argv[2] ?? resolve('.'));

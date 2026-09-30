# packages/api-client

Shared TypeScript client for the Learn-and-Reward API.

`apps/web/lib/api.ts` currently contains a hand-written typed client matching
`docs/contracts/openapi-mission-b.json`. Once the OpenAPI contract is frozen with
Developers A and C, generate this package from the contract instead:

```bash
npx openapi-typescript ../docs/contracts/openapi.json -o ./src/schema.d.ts
```

and have the web app import the generated types from here.

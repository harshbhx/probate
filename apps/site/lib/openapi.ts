import { createOpenAPI } from 'fumadocs-openapi/server';

// The Courthouse's API, exported from the FastAPI app by `make api-spec`
// (scripts/export_openapi.py). Examples in it come from a real simulated family.
export const openapi = createOpenAPI({
  input: ['./openapi.json'],
});

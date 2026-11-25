// The Courthouse's OpenAPI schema, served for agents and the ARD manifest (exported by scripts/export_openapi.py).
import spec from '../../openapi.json';

export const revalidate = false;

export function GET() {
  return Response.json(spec);
}

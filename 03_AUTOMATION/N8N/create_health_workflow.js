const fs = require('fs');
const workflowPath = '<HOME>/.n8n/workflow-imports/health_check_periodic.json';
const projectId = 'x7R2jO2iP6TVUP5b';
const base = 'http://127.0.0.1:5678';
const loginBody = { emailOrLdapLoginId: 'localai-n8n@example.com', password: 'LocalAI!2026' };
async function main() {
  const login = await fetch(base + '/rest/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(loginBody),
  });
  const cookie = login.headers.get('set-cookie');
  if (!login.ok || !cookie) throw new Error('login failed ' + login.status + ' ' + await login.text());
  const body = JSON.parse(fs.readFileSync(workflowPath, 'utf8'));
  body.projectId = projectId;
  body.active = false;
  const create = await fetch(base + '/rest/workflows', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', cookie },
    body: JSON.stringify(body),
  });
  const createText = await create.text();
  console.log('CREATE_STATUS', create.status);
  console.log(createText);
  if (!create.ok) return;
  const created = JSON.parse(createText);
  const activate = await fetch(base + '/rest/workflows/' + created.id + '/activate', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', cookie },
    body: JSON.stringify({ expectedChecksum: created.checksum, versionId: created.versionId, name: created.name, description: created.description || '' }),
  });
  console.log('ACTIVATE_STATUS', activate.status);
  console.log(await activate.text());
}
main().catch(err => { console.error(err); process.exit(1); });

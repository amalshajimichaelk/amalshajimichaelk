/**
 * Cloudflare Worker webhook receiver for GitHub App push events.
 *
 * Validates webhook signatures, processes push events, and dispatches
 * GitHub Actions workflow to update the contribution tracker.
 */

interface Env {
  GITHUB_WEBHOOK_SECRET: string;
  GITHUB_APP_ID: string;
  GITHUB_APP_PRIVATE_KEY: string;
  PROFILE_REPO_OWNER: string;
  PROFILE_REPO_NAME: string;
}

interface WebhookPayload {
  action?: string;
  repository?: {
    full_name: string;
    private: boolean;
    owner: {
      login: string;
    };
    name: string;
  };
  sender?: {
    login: string;
  };
  commits?: Array<{
    author: {
      username?: string;
      name?: string;
      email?: string;
    };
  }>;
  ref?: string;
}

/**
 * Verify GitHub webhook signature using HMAC SHA-256.
 */
async function verifySignature(
  payload: string,
  signature: string,
  secret: string
): Promise<boolean> {
  if (!signature || !signature.startsWith('sha256=')) {
    return false;
  }

  const signatureHash = signature.slice(7); // Remove 'sha256=' prefix

  const encoder = new TextEncoder();
  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signatureBytes = await crypto.subtle.sign(
    'HMAC',
    key,
    encoder.encode(payload)
  );

  const expectedHash = Array.from(new Uint8Array(signatureBytes))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');

  // Constant-time comparison to prevent timing attacks
  if (expectedHash.length !== signatureHash.length) {
    return false;
  }

  let mismatch = 0;
  for (let i = 0; i < expectedHash.length; i++) {
    mismatch |= expectedHash.charCodeAt(i) ^ signatureHash.charCodeAt(i);
  }

  return mismatch === 0;
}

/**
 * Generate GitHub App installation token using JWT.
 */
async function getInstallationToken(
  appId: string,
  privateKey: string,
  installationId: number
): Promise<string> {
  // Generate JWT for GitHub App authentication
  const now = Math.floor(Date.now() / 1000);

  const header = {
    alg: 'RS256',
    typ: 'JWT',
  };

  const payload = {
    iat: now - 60, // Issued 60 seconds in the past to account for clock drift
    exp: now + 600, // Expires in 10 minutes
    iss: appId,
  };

  // Create JWT (simplified - in production, use a proper JWT library)
  const headerBase64 = btoa(JSON.stringify(header));
  const payloadBase64 = btoa(JSON.stringify(payload));
  const signatureInput = `${headerBase64}.${payloadBase64}`;

  // Import private key
  const pemKey = privateKey.replace(/\\n/g, '\n');
  const keyData = pemKey
    .replace('-----BEGIN RSA PRIVATE KEY-----', '')
    .replace('-----END RSA PRIVATE KEY-----', '')
    .replace(/\s/g, '');

  const binaryKey = Uint8Array.from(atob(keyData), c => c.charCodeAt(0));

  const cryptoKey = await crypto.subtle.importKey(
    'pkcs8',
    binaryKey,
    {
      name: 'RSASSA-PKCS1-v1_5',
      hash: 'SHA-256',
    },
    false,
    ['sign']
  );

  const signature = await crypto.subtle.sign(
    'RSASSA-PKCS1-v1_5',
    cryptoKey,
    new TextEncoder().encode(signatureInput)
  );

  const signatureBase64 = btoa(String.fromCharCode(...new Uint8Array(signature)));
  const jwt = `${signatureInput}.${signatureBase64}`;

  // Get installation access token
  const response = await fetch(
    `https://api.github.com/app/installations/${installationId}/access_tokens`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${jwt}`,
        Accept: 'application/vnd.github.v3+json',
        'User-Agent': 'github-profile-webhook',
      },
    }
  );

  if (!response.ok) {
    throw new Error(`Failed to get installation token: ${response.status}`);
  }

  const data = await response.json() as { token: string };
  return data.token;
}

/**
 * Dispatch GitHub Actions workflow.
 */
async function dispatchWorkflow(
  token: string,
  owner: string,
  repo: string,
  workflowId: string,
  inputs: Record<string, string>
): Promise<boolean> {
  const response = await fetch(
    `https://api.github.com/repos/${owner}/${repo}/actions/workflows/${workflowId}/dispatches`,
    {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/vnd.github.v3+json',
        'User-Agent': 'github-profile-webhook',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        ref: 'main',
        inputs,
      }),
    }
  );

  return response.status === 204;
}

/**
 * Process deduplication using KV (optional enhancement).
 */
const processedDeliveries = new Set<string>();

function isDuplicate(deliveryId: string): boolean {
  if (processedDeliveries.has(deliveryId)) {
    return true;
  }
  processedDeliveries.add(deliveryId);

  // Clean up old entries (keep last 1000)
  if (processedDeliveries.size > 1000) {
    const entries = Array.from(processedDeliveries);
    processedDeliveries.clear();
    entries.slice(-500).forEach(id => processedDeliveries.add(id));
  }

  return false;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    // Only accept POST requests
    if (request.method !== 'POST') {
      return new Response('Method not allowed', { status: 405 });
    }

    try {
      // Get headers
      const signature = request.headers.get('X-Hub-Signature-256');
      const event = request.headers.get('X-GitHub-Event');
      const deliveryId = request.headers.get('X-GitHub-Delivery');

      if (!signature || !event || !deliveryId) {
        return new Response('Missing required headers', { status: 400 });
      }

      // Check for duplicate delivery
      if (isDuplicate(deliveryId)) {
        console.log(`Duplicate delivery: ${deliveryId}`);
        return new Response('Duplicate delivery', { status: 200 });
      }

      // Read and verify payload
      const payloadText = await request.text();

      const isValid = await verifySignature(
        payloadText,
        signature,
        env.GITHUB_WEBHOOK_SECRET
      );

      if (!isValid) {
        console.error('Invalid signature');
        return new Response('Invalid signature', { status: 401 });
      }

      const payload: WebhookPayload = JSON.parse(payloadText);

      // Only process push events
      if (event !== 'push') {
        console.log(`Ignoring event: ${event}`);
        return new Response('Event ignored', { status: 200 });
      }

      // Ignore private repositories
      if (payload.repository?.private) {
        console.log(`Ignoring private repository: ${payload.repository.full_name}`);
        return new Response('Private repo ignored', { status: 200 });
      }

      const repositoryFullName = payload.repository?.full_name;
      if (!repositoryFullName) {
        return new Response('Missing repository info', { status: 400 });
      }

      console.log(`Processing push to: ${repositoryFullName}`);

      // Note: Actual commit author verification happens in the GitHub Actions workflow
      // The webhook receiver just triggers the workflow with repository information

      // Get installation token (you'll need to add installation_id to env or fetch it)
      // For simplicity, using a workflow dispatch with a pre-configured token
      // In production, implement proper GitHub App authentication

      // Dispatch workflow to update profile
      const workflowInputs = {
        source_repository: repositoryFullName,
        delivery_id: deliveryId,
        event_type: 'push',
      };

      // For now, this is a placeholder - you'll need to configure authentication
      // Option 1: Use GitHub App installation token
      // Option 2: Use a fine-grained PAT with workflow dispatch permission
      // Option 3: Use repository dispatch event instead

      console.log(`Webhook processed for ${repositoryFullName}`);

      return new Response(
        JSON.stringify({
          status: 'accepted',
          repository: repositoryFullName,
          delivery_id: deliveryId,
        }),
        {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        }
      );

    } catch (error) {
      console.error('Webhook processing error:', error);
      return new Response('Internal server error', { status: 500 });
    }
  },
};

import { Pool } from "pg";
import { randomUUID } from "crypto";

const connectionString =
  process.env.PLAYWRIGHT_DB_URL ?? "postgresql://whago:whago123@localhost:5432/whago";

const pool = new Pool({
  connectionString,
});

export async function deleteUserByEmail(email: string): Promise<void> {
  await pool.query("DELETE FROM users WHERE email = $1", [email.toLowerCase()]);
}

export async function insertNotification(options: {
  userId: string;
  title: string;
  message?: string;
  type?: "info" | "success" | "warning" | "error";
}): Promise<void> {
  const { userId, title, message = null, type = "info" } = options;
  await pool.query(
    `
      INSERT INTO notifications (id, user_id, title, message, type, is_read, created_at)
      VALUES ($1::uuid, $2::uuid, $3, $4, $5, false, NOW())
    `,
    [randomUUID(), userId, title, message, type],
  );
}

export async function insertCampaignWithMessage(options: {
  userId: string;
  name?: string;
  recipient?: string;
}): Promise<{ campaignId: string }> {
  const campaignId = randomUUID();
  const contactId = randomUUID();
  const messageId = randomUUID();
  const name = options.name ?? "Campanha Playwright";
  const recipient = options.recipient ?? "+5511987654321";

  await pool.query(
    `
      INSERT INTO campaigns (
        id, user_id, name, description, type, status, message_template,
        total_contacts, sent_count, delivered_count, read_count, failed_count,
        credits_consumed, created_at
      )
      VALUES (
        $1::uuid, $2::uuid, $3, 'Campanha criada em testes E2E', 'simple', 'running',
        'Olá {{name}}! Bem-vindo ao WHAGO.',
        10, 6, 4, 2, 1, 5, NOW()
      )
    `,
    [campaignId, options.userId, name],
  );

  await pool.query(
    `
      INSERT INTO campaign_contacts (id, campaign_id, phone_number, name, created_at)
      VALUES ($1::uuid, $2::uuid, $3, 'Contato E2E', NOW())
    `,
    [contactId, campaignId, recipient],
  );

  await pool.query(
    `
      INSERT INTO campaign_messages (
        id, campaign_id, contact_id, content, status,
        sent_at, delivered_at, read_at, created_at
      )
      VALUES (
        $1::uuid, $2::uuid, $3::uuid, 'Mensagem de teste enviada via Playwright.',
        'sent', NOW(), NOW(), NULL, NOW()
      )
    `,
    [messageId, campaignId, contactId],
  );

  return { campaignId };
}

export async function closeConnectionPool(): Promise<void> {
  await pool.end();
}


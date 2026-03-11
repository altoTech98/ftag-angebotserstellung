import { Resend } from 'resend';

export const resend = new Resend(process.env.RESEND_API_KEY || 're_placeholder');

export const EMAIL_FROM =
  process.env.RESEND_FROM_EMAIL ||
  'FTAG Angebotserstellung <onboarding@resend.dev>';

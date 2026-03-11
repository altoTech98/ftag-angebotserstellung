import {
  Html,
  Head,
  Body,
  Container,
  Text,
  Section,
  Hr,
} from '@react-email/components';

interface PasswordResetEmailProps {
  otp: string;
  name: string;
}

export function PasswordResetEmail({ otp, name }: PasswordResetEmailProps) {
  return (
    <Html lang="de">
      <Head />
      <Body style={body}>
        <Container style={container}>
          <Text style={logo}>FTAG Angebotserstellung</Text>
          <Hr style={redLine} />

          <Section style={content}>
            <Text style={heading}>Passwort zuruecksetzen</Text>
            <Text style={paragraph}>
              Hallo {name}, Ihr Verifizierungscode lautet:
            </Text>

            <Section style={otpContainer}>
              <Text style={otpText}>{otp}</Text>
            </Section>

            <Text style={note}>
              Dieser Code ist 10 Minuten gueltig.
            </Text>
          </Section>

          <Hr style={divider} />
          <Text style={footer}>Frank Tueren AG, Buochs NW</Text>
        </Container>
      </Body>
    </Html>
  );
}

const body = {
  backgroundColor: '#f6f6f6',
  fontFamily: 'Arial, sans-serif',
};

const container = {
  backgroundColor: '#ffffff',
  maxWidth: '480px',
  margin: '0 auto',
  padding: '24px',
};

const logo = {
  fontWeight: 'bold' as const,
  fontSize: '18px',
  color: '#111827',
  margin: '0 0 8px 0',
};

const redLine = {
  borderColor: '#dc2626',
  borderWidth: '2px',
  margin: '0 0 24px 0',
};

const content = {
  padding: '0',
};

const heading = {
  fontSize: '20px',
  fontWeight: 'bold' as const,
  color: '#111827',
  margin: '0 0 16px 0',
};

const paragraph = {
  fontSize: '14px',
  color: '#374151',
  lineHeight: '1.5',
  margin: '0 0 16px 0',
};

const otpContainer = {
  backgroundColor: '#f3f4f6',
  borderRadius: '8px',
  padding: '16px',
  textAlign: 'center' as const,
  margin: '0 0 16px 0',
};

const otpText = {
  fontSize: '32px',
  fontWeight: 'bold' as const,
  letterSpacing: '4px',
  color: '#111827',
  margin: '0',
};

const note = {
  fontSize: '12px',
  color: '#6b7280',
  margin: '0 0 24px 0',
};

const divider = {
  borderColor: '#e5e7eb',
  margin: '0 0 16px 0',
};

const footer = {
  fontSize: '12px',
  color: '#6b7280',
  margin: '0',
};

export default PasswordResetEmail;

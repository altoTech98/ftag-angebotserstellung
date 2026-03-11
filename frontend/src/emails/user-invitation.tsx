import {
  Html,
  Head,
  Body,
  Container,
  Text,
  Section,
  Hr,
  Button,
} from '@react-email/components';

interface UserInvitationEmailProps {
  name: string;
  invitedBy: string;
  loginUrl: string;
}

export function UserInvitationEmail({
  name,
  invitedBy,
  loginUrl,
}: UserInvitationEmailProps) {
  return (
    <Html lang="de">
      <Head />
      <Body style={body}>
        <Container style={container}>
          <Text style={logo}>FTAG Angebotserstellung</Text>
          <Hr style={redLine} />

          <Section style={content}>
            <Text style={heading}>Sie wurden eingeladen</Text>
            <Text style={paragraph}>
              Hallo {name}, {invitedBy} hat Sie zur FTAG Angebotserstellung
              eingeladen.
            </Text>
            <Text style={paragraph}>
              Sie koennen sich ab sofort anmelden und Ihr Passwort bei der
              ersten Anmeldung aendern.
            </Text>

            <Section style={buttonContainer}>
              <Button style={button} href={loginUrl}>
                Jetzt anmelden
              </Button>
            </Section>
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

const buttonContainer = {
  textAlign: 'center' as const,
  margin: '24px 0',
};

const button = {
  backgroundColor: '#dc2626',
  color: '#ffffff',
  fontSize: '14px',
  fontWeight: 'bold' as const,
  padding: '12px 24px',
  borderRadius: '6px',
  textDecoration: 'none',
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

export default UserInvitationEmail;

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

interface AnalysisCompleteEmailProps {
  userName: string;
  projectName: string;
  matchCount: number;
  gapCount: number;
  avgConfidence: number;
  resultUrl: string;
}

export function AnalysisCompleteEmail({
  userName,
  projectName,
  matchCount,
  gapCount,
  avgConfidence,
  resultUrl,
}: AnalysisCompleteEmailProps) {
  return (
    <Html lang="de">
      <Head />
      <Body style={body}>
        <Container style={container}>
          <Text style={logo}>FTAG Angebotserstellung</Text>
          <Hr style={redLine} />

          <Section style={content}>
            <Text style={heading}>Analyse abgeschlossen</Text>
            <Text style={paragraph}>
              Hallo {userName}, die Analyse fuer Projekt &lsquo;{projectName}
              &rsquo; wurde abgeschlossen.
            </Text>

            <Section style={statsContainer}>
              <table style={statsTable}>
                <tbody>
                  <tr>
                    <td style={statsLabel}>Matches:</td>
                    <td style={statsValue}>{matchCount}</td>
                  </tr>
                  <tr>
                    <td style={statsLabel}>Gaps:</td>
                    <td style={statsValue}>{gapCount}</td>
                  </tr>
                  <tr>
                    <td style={statsLabel}>Konfidenz:</td>
                    <td style={statsValue}>{avgConfidence}%</td>
                  </tr>
                </tbody>
              </table>
            </Section>

            <Section style={buttonContainer}>
              <Button style={button} href={resultUrl}>
                Ergebnisse ansehen
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

const statsContainer = {
  backgroundColor: '#f3f4f6',
  borderRadius: '8px',
  padding: '16px',
  margin: '0 0 24px 0',
};

const statsTable = {
  width: '100%',
  borderCollapse: 'collapse' as const,
};

const statsLabel = {
  fontSize: '14px',
  color: '#6b7280',
  padding: '4px 0',
};

const statsValue = {
  fontSize: '14px',
  fontWeight: 'bold' as const,
  color: '#111827',
  textAlign: 'right' as const,
  padding: '4px 0',
};

const buttonContainer = {
  textAlign: 'center' as const,
  margin: '0 0 24px 0',
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

export default AnalysisCompleteEmail;

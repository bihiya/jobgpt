import { createTheme, ThemeProvider } from '@mui/material/styles';
import { render, screen } from '@testing-library/react';
import ResumeVersions from '../src/components/profile/ResumeVersions';

function renderVersions(props = {}) {
  const resumes = props.resumes ?? [
    {
      id: 'r1',
      name: 'Lav_Gupta_Resume.pdf',
      file_type: 'pdf',
      is_default: true,
      created_at: '2026-08-15T07:15:13',
    },
  ];
  const onUpload = props.onUpload ?? (() => {});
  const onDownload = props.onDownload ?? (() => {});
  const onDelete = props.onDelete ?? (() => {});
  return render(
    <ThemeProvider theme={createTheme()}>
      <ResumeVersions
        resumes={resumes}
        previewUrl={props.previewUrl ?? null}
        previewName={props.previewName ?? ''}
        uploading={props.uploading}
        busyId={props.busyId}
        onUpload={onUpload}
        onDownload={onDownload}
        onDelete={onDelete}
      />
    </ThemeProvider>,
  );
}

describe('ResumeVersions', () => {
  it('shows the uploaded resume name, upload time, and download', () => {
    renderVersions();
    expect(screen.getByText('Lav_Gupta_Resume.pdf')).toBeInTheDocument();
    expect(screen.getByText('Default')).toBeInTheDocument();
    expect(screen.getByText(/Uploaded /)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Download' })).toBeInTheDocument();
  });

  it('disables upload at 5 versions', () => {
    const resumes = Array.from({ length: 5 }, (_, i) => ({
      id: `r${i}`,
      name: `cv-${i}.pdf`,
      file_type: 'pdf',
      is_default: i === 0,
      created_at: '2026-08-15T07:15:13',
    }));
    renderVersions({ resumes });
    expect(screen.getByRole('button', { name: 'Upload resume' })).toHaveAttribute(
      'aria-disabled',
      'true',
    );
    expect(screen.getByText(/max 5/i)).toBeInTheDocument();
  });

  it('renders a PDF preview iframe when a blob URL is provided', () => {
    renderVersions({ previewUrl: 'blob:http://localhost/preview', previewName: 'Lav_Gupta_Resume.pdf' });
    expect(screen.getByTitle('Resume preview')).toBeInTheDocument();
    expect(screen.getByText(/Preview — Lav_Gupta_Resume.pdf/)).toBeInTheDocument();
  });
});

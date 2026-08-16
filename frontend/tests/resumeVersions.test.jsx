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
  const onSelect = props.onSelect;
  return render(
    <ThemeProvider theme={createTheme()}>
      <ResumeVersions
        resumes={resumes}
        previewUrl={props.previewUrl ?? null}
        previewName={props.previewName ?? ''}
        uploading={props.uploading}
        busyId={props.busyId}
        selectedId={props.selectedId}
        onUpload={onUpload}
        onDownload={onDownload}
        onDelete={onDelete}
        onSelect={onSelect}
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

  it('keeps upload enabled at 5 versions and explains the rolling window', () => {
    const resumes = Array.from({ length: 5 }, (_, i) => ({
      id: `r${i}`,
      name: `cv-${i}.pdf`,
      file_type: 'pdf',
      is_default: i === 0,
      created_at: '2026-08-15T07:15:13',
    }));
    renderVersions({ resumes });
    expect(screen.getByRole('button', { name: 'Upload resume' })).not.toHaveAttribute(
      'aria-disabled',
      'true',
    );
    expect(screen.getByText(/All 5 resumes/)).toBeInTheDocument();
    expect(screen.getByText(/removes the oldest/i)).toBeInTheDocument();
  });

  it('lists every resume version', () => {
    const resumes = [
      {
        id: 'r1',
        name: 'cv-latest.pdf',
        file_type: 'pdf',
        is_default: true,
        created_at: '2026-08-16T01:00:00',
      },
      {
        id: 'r2',
        name: 'cv-mid.pdf',
        file_type: 'pdf',
        is_default: false,
        created_at: '2026-08-15T12:00:00',
      },
      {
        id: 'r3',
        name: 'cv-old.docx',
        file_type: 'docx',
        is_default: false,
        created_at: '2026-08-14T08:00:00',
      },
    ];
    renderVersions({ resumes, onSelect: () => {} });
    expect(screen.getByText('cv-latest.pdf')).toBeInTheDocument();
    expect(screen.getByText('cv-mid.pdf')).toBeInTheDocument();
    expect(screen.getByText('cv-old.docx')).toBeInTheDocument();
    expect(screen.getByText(/All 3 resumes/)).toBeInTheDocument();
    expect(screen.getAllByRole('button', { name: 'View' })).toHaveLength(2);
  });

  it('renders a PDF preview iframe when a blob URL is provided', () => {
    renderVersions({ previewUrl: 'blob:http://localhost/preview', previewName: 'Lav_Gupta_Resume.pdf' });
    expect(screen.getByTitle('Resume preview')).toBeInTheDocument();
    expect(screen.getByText(/Preview — Lav_Gupta_Resume.pdf/)).toBeInTheDocument();
  });
});

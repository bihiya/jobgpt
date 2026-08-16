import {
  Box,
  Button,
  Chip,
  Paper,
  Stack,
  Typography,
} from '@mui/material';
import { formatWhenLong } from '../../utils/datetime';

export const MAX_RESUME_VERSIONS = 5;

export type ResumeVersion = {
  id: string;
  name: string;
  file_type: string;
  is_default: boolean;
  created_at: string;
};

type Props = {
  resumes: ResumeVersion[];
  uploading?: boolean;
  loading?: boolean;
  busyId?: string | null;
  previewUrl?: string | null;
  previewName?: string;
  selectedId?: string | null;
  onUpload: (file: File) => void;
  onDownload: (resume: ResumeVersion) => void;
  onDelete: (resume: ResumeVersion) => void;
  onSelect?: (resume: ResumeVersion) => void;
};

export default function ResumeVersions({
  resumes,
  uploading = false,
  loading = false,
  busyId = null,
  previewUrl = null,
  previewName = '',
  selectedId = null,
  onUpload,
  onDownload,
  onDelete,
  onSelect,
}: Props) {
  return (
    <Stack spacing={1.5}>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        spacing={1}
        alignItems={{ sm: 'center' }}
        justifyContent="space-between"
      >
        <Box>
          <Typography variant="h5">Resumes</Typography>
          <Typography color="text.secondary">
            All {resumes.length} resume{resumes.length === 1 ? '' : 's'} — keeps the{' '}
            {MAX_RESUME_VERSIONS} newest; a new upload removes the oldest.
          </Typography>
        </Box>
        <Button variant="outlined" component="label" disabled={uploading}>
          {uploading ? 'Uploading…' : 'Upload resume'}
          <input
            hidden
            type="file"
            accept=".pdf,.doc,.docx"
            onChange={(e) => {
              const file = e.target.files?.[0];
              e.target.value = '';
              if (file) onUpload(file);
            }}
          />
        </Button>
      </Stack>

      {loading && (
        <Typography color="text.secondary">Loading resumes…</Typography>
      )}
      {!loading && resumes.length === 0 && (
        <Typography color="text.secondary">No resumes uploaded yet.</Typography>
      )}

      {resumes.map((resume) => (
        <Paper
          key={resume.id}
          variant="outlined"
          sx={{
            p: 1.5,
            borderColor: selectedId === resume.id ? 'primary.main' : 'divider',
            bgcolor: selectedId === resume.id ? 'action.selected' : 'background.paper',
          }}
        >
          <Stack
            direction={{ xs: 'column', sm: 'row' }}
            spacing={1}
            alignItems={{ sm: 'center' }}
            justifyContent="space-between"
          >
            <Box sx={{ minWidth: 0 }}>
              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
                <Typography fontWeight={600} noWrap title={resume.name}>
                  {resume.name}
                </Typography>
                {resume.is_default && <Chip size="small" color="success" label="Default" />}
                <Chip size="small" variant="outlined" label={(resume.file_type || 'file').toUpperCase()} />
              </Stack>
              <Typography color="text.secondary" variant="body2">
                Uploaded {formatWhenLong(resume.created_at)}
              </Typography>
            </Box>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              {(resume.file_type || '').toLowerCase() === 'pdf' && onSelect && (
                <Button
                  size="small"
                  disabled={busyId === resume.id}
                  onClick={() => onSelect(resume)}
                >
                  View
                </Button>
              )}
              <Button
                size="small"
                disabled={busyId === resume.id}
                onClick={() => onDownload(resume)}
              >
                Download
              </Button>
              <Button
                size="small"
                color="error"
                disabled={busyId === resume.id}
                onClick={() => onDelete(resume)}
              >
                Delete
              </Button>
            </Stack>
          </Stack>
        </Paper>
      ))}

      {previewUrl && (
        <Box>
          <Typography variant="subtitle2" sx={{ mb: 0.5 }}>
            Preview{previewName ? ` — ${previewName}` : ''}
          </Typography>
          <Box
            sx={{
              height: { xs: 420, sm: 560 },
              border: 1,
              borderColor: 'divider',
              borderRadius: 1,
              overflow: 'hidden',
              bgcolor: 'background.paper',
            }}
          >
            <iframe
              title="Resume preview"
              src={previewUrl}
              style={{ width: '100%', height: '100%', border: 0 }}
            />
          </Box>
        </Box>
      )}
    </Stack>
  );
}

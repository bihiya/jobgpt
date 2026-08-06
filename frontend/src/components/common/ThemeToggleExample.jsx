/**
 * Example: reading Redux state and dispatching actions with hooks.
 * Used by Dark Mode control; mirrors interview-quality RTK patterns.
 */
import { IconButton } from '@mui/material';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import LightModeIcon from '@mui/icons-material/LightMode';
import { useDispatch, useSelector } from 'react-redux';
import { toggleDarkMode } from '../../store/slices/uiSlice';

export default function ThemeToggleExample() {
  const dispatch = useDispatch();
  const darkMode = useSelector((state) => state.ui.darkMode);

  return (
    <IconButton aria-label="Toggle theme" onClick={() => dispatch(toggleDarkMode())}>
      {darkMode ? <LightModeIcon /> : <DarkModeIcon />}
    </IconButton>
  );
}

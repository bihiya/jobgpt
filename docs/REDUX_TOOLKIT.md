# Redux Toolkit Setup (JavaScript)

Interview-quality RTK structure used by JobPilot AI for global UI/auth state.
Server data uses TanStack Query; Redux holds session + UI chrome.

## Folder structure

```
frontend/src/store/
├── store.js                 # configureStore + combined reducers
├── hooks.ts                 # useAppDispatch / useAppSelector
└── slices/
    ├── authSlice.js         # session credentials
    └── uiSlice.js           # dark mode, sidebar, snackbar
```


## Store setup

```js
// store/store.js
import { configureStore } from '@reduxjs/toolkit';
import authReducer from './slices/authSlice';
import uiReducer from './slices/uiSlice';

export const store = configureStore({
  reducer: {
    auth: authReducer,
    ui: uiReducer,
  },
});
```

## Slice example

```js
// store/slices/authSlice.js
import { createSlice } from '@reduxjs/toolkit';

const authSlice = createSlice({
  name: 'auth',
  initialState: { user: null, accessToken: null, isAuthenticated: false },
  reducers: {
    setCredentials(state, action) {
      state.user = action.payload.user;
      state.accessToken = action.payload.accessToken;
      state.isAuthenticated = true;
    },
    logout(state) {
      state.user = null;
      state.accessToken = null;
      state.isAuthenticated = false;
    },
  },
});

export const { setCredentials, logout } = authSlice.actions;
export default authSlice.reducer;
```

## React usage example

```jsx
import { useDispatch, useSelector } from 'react-redux';
import { toggleDarkMode } from '../store/slices/uiSlice';

function ThemeToggle() {
  const dispatch = useDispatch();
  const darkMode = useSelector((state) => state.ui.darkMode);
  return (
    <button onClick={() => dispatch(toggleDarkMode())}>
      {darkMode ? 'Light' : 'Dark'}
    </button>
  );
}
```

See also: `frontend/src/components/common/ThemeToggleExample.jsx`

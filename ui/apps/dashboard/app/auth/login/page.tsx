import { Suspense } from 'react';
import LoginRoute from './login-route';

function LoadingSpinner() {
  return <div>Loading...</div>;
}

export default function LoginPageContainer() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <Suspense fallback={<LoadingSpinner />}>
        <LoginRoute />
      </Suspense>
    </div>
  );
}

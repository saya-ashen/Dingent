import { Suspense } from 'react';
import LoginRoute from './sign-up-route';

function LoadingSpinner() {
  return <div>Loading...</div>;
}

export default function SignUpPageContainer() {
  return (
    <div className="flex items-center justify-center min-h-screen">
      <Suspense fallback={<LoadingSpinner />}>
        <LoginRoute />
      </Suspense>
    </div>
  );
}

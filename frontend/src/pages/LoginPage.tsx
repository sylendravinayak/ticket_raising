import LoginForm from '@/features/auth/components/LoginForm';

export default function LoginPage() {
  return (
    <>
      <h2 className="text-xl font-bold text-center text-gray-900 mb-6">
        Sign in to your account
      </h2>
      <LoginForm />
    </>
  );
}

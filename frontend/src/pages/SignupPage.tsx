import SignupForm from '@/features/auth/components/SignupForm';

export default function SignupPage() {
  return (
    <>
      <h2 className="text-xl font-bold text-center text-gray-900 mb-6">
        Create your account
      </h2>
      <SignupForm />
    </>
  );
}

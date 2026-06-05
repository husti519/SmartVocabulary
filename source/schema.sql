-- Users table (Extends Supabase Auth)
CREATE TABLE IF NOT EXISTS public.profiles (
    id UUID REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
    username TEXT UNIQUE,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Card Sets table
CREATE TABLE IF NOT EXISTS public.card_sets (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE,
    title TEXT UNIQUE,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_studied_at TIMESTAMP WITH TIME ZONE DEFAULT NULL
);

-- Cards table
CREATE TABLE IF NOT EXISTS public.cards (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    cardset_id UUID REFERENCES public.card_sets(id) ON DELETE CASCADE NOT NULL,
    word TEXT,
    definition TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    starred BOOLEAN DEFAULT FALSE
);

-- Enable Row Level Security (RLS)
ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.card_sets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cards ENABLE ROW LEVEL SECURITY;

-- Policies
CREATE POLICY "Profiles are viewable by owner only." ON public.profiles FOR SELECT TO authenticated USING (auth.uid() = id);
CREATE POLICY "Users can insert their own profile." ON public.profiles FOR INSERT TO authenticated WITH CHECK (auth.uid() = id);
CREATE POLICY "Users can update their own profile." ON public.profiles FOR UPDATE TO authenticated USING (auth.uid() = id);

CREATE POLICY "Users can view their own card sets." ON public.card_sets FOR SELECT TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Users can create their own card sets." ON public.card_sets FOR INSERT TO authenticated WITH CHECK (auth.uid() = user_id);
CREATE POLICY "Users can update their own card sets." ON public.card_sets FOR UPDATE TO authenticated USING (auth.uid() = user_id);
CREATE POLICY "Users can delete their own card sets." ON public.card_sets FOR DELETE TO authenticated USING (auth.uid() = user_id);

CREATE POLICY "Users can view their own cards" ON public.cards FOR SELECT TO authenticated USING ( user_id = auth.uid() );
CREATE POLICY "Users can insert their own cards" ON public.cards FOR INSERT TO authenticated WITH CHECK ( user_id = auth.uid() );
CREATE POLICY "Users can update their own cards" ON public.cards FOR UPDATE TO authenticated USING ( user_id = auth.uid() ) WITH CHECK ( user_id = auth.uid() );
CREATE POLICY "Users can delete their own cards" ON public.cards FOR DELETE TO authenticated USING ( user_id = auth.uid() );

-- grants
GRANT SELECT, INSERT, UPDATE, DELETE on public.profiles to authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.card_sets TO authenticated;
GRANT SELECT, INSERT, UPDATE, DELETE ON public.cardS TO authenticated;

-- 현재 로그인한 사용자를 auth.users에서 삭제하는 함수
CREATE OR REPLACE FUNCTION delete_user()
RETURNS void
LANGUAGE SQL
SECURITY DEFINER -- 이 함수는 데이터베이스 관리자 권한으로 실행됨
AS $$
  DELETE FROM auth.users WHERE id = auth.uid();
$$;
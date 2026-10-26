from database import Base, engine
from models import BrandVoice, GeneratedContent, User


def main():
    Base.metadata.create_all(bind=engine)
    print("CreatorOS database tables created successfully.")


if __name__ == "__main__":
    main()

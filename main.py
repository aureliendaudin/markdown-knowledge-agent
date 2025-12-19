"""Main CLI entry point."""
import sys
from pathlib import Path
from config import settings, load_config
from utils import setup_logging
from core import ObsidianAgent


def main():
    """Run interactive CLI."""
    # Check config exists
    if settings is None:
        print("❌ No configuration file found!")
        print("💡 Copy config.yaml.example to config.yaml and edit it:")
        print("   cp config.yaml.example config.yaml")
        sys.exit(1)
    
    # Setup logging
    setup_logging(settings.logging.level)
    
    # Validate configuration
    try:
        settings.validate_setup()
    except ValueError as e:
        print(f"❌ Configuration error: {e}")
        sys.exit(1)
    
    # Initialize agent
    print("🤖 Initializing Obsidian Agent...")
    agent = ObsidianAgent()
    
    print(f"\n✅ Agent ready!")
    print(f"📦 Model: {settings.model.ollama.model if settings.model.provider == 'ollama' else settings.model.anthropic.model}")
    print(f"📁 Vault: {settings.vault.path}")
    print(f"🔧 Modules: {', '.join(name for name, m in agent.modules.items() if m.enabled)}")
    
    # Examples
    examples = [
        "Quels sont mes cours d'IA ?",
        "Trouve mes notes sur PyTorch",
        "Lis School/Notes/AI/Machine Learning.md",
        "Cherche 'ovarian' dans Oncology"
    ]
    
    print("\n💡 Exemples de questions:")
    for i, ex in enumerate(examples, 1):
        print(f"  {i}. {ex}")
    
    print("\n" + "="*60)
    
    # Interactive loop
    while True:
        try:
            question = input("\n❓ Vous: ").strip()
            if not question:
                continue
            if question.lower() in ['exit', 'quit', 'q']:
                break
                
            result = agent.ask(question)
            
            if isinstance(result, dict):
                answer = result["answer"]
                # Optionally print logs in CLI
                # for log in result["logs"]:
                #     print(f"  [LOG] {log}")
            else:
                answer = result
                
            print(f"\n🤖 Agent: {answer}")
            print("\n" + "-"*40)
            
        except KeyboardInterrupt:
            print("\n👋 Au revoir!")
            break
        except Exception as e:
            print(f"\n❌ Erreur: {e}")
    
            if settings.logging.level == "DEBUG":
                import traceback
                traceback.print_exc()
            continue


if __name__ == "__main__":
    main()

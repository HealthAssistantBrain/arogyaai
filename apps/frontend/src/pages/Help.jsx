import { HelpCircle, Search, MessageSquare, Book, LifeBuoy } from 'lucide-react';
import PageWrapper from '../components/layout/PageWrapper';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';

const Help = () => {
  return (
    <PageWrapper>
      <div className="max-w-3xl mx-auto w-full space-y-8">
        <div className="text-center space-y-3">
          <h2 className="text-3xl font-extrabold text-text-primary tracking-tight">How can we help?</h2>
          <p className="text-text-secondary text-sm">Find answers to common questions about your health tracking.</p>
        </div>

        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-text-muted w-5 h-5" />
          <input
            type="text"
            placeholder="Search topics, e.g. HRV, Lab Results..."
            className="w-full bg-white border-2 border-[#EEEEEE] rounded-2xl px-12 py-4 shadow-sm focus:border-primary focus:outline-none transition-all"
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {[
            { icon: Book, title: 'Knowledge Base', desc: 'Detailed guides on every health metric.' },
            { icon: MessageSquare, title: 'Direct Chat', desc: 'Talk to our health support team.' },
            { icon: LifeBuoy, title: 'App Issues', desc: 'Troubleshoot wearable sync problems.' },
            { icon: HelpCircle, title: 'FAQ', desc: 'Common questions and quick answers.' },
          ].map((item, idx) => (
            <Card key={idx} className="cursor-pointer hover:border-primary/20 transition-all flex flex-col gap-3">
              <item.icon className="w-6 h-6 text-primary" />
              <h4 className="text-sm font-bold">{item.title}</h4>
              <p className="text-[11px] text-text-secondary">{item.desc}</p>
            </Card>
          ))}
        </div>
      </div>
    </PageWrapper>
  );
};

export default Help;

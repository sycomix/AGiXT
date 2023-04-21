import { useRouter } from 'next/router';
import axios from 'axios';
import useSWR from 'swr';
import AgentControl from '@/components/agent/AgentControl';
import ContentSWR from '@/components/content/ContentSWR';
export default function Agent() {
    const agentName = useRouter().query.agent;
    const agent = useSWR(`agent/${agentName}`, async () => (await axios.get(`${process.env.API_URI ?? 'http://localhost:5000'}/api/agent/${agentName}`)).data);
    return <ContentSWR swr={agent} content={AgentControl} />;
}
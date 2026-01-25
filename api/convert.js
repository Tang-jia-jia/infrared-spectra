// api/convert.js
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(
    process.env.SUPABASE_URL,
    process.env.SUPABASE_SERVICE_KEY
);

export default async function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ error: '只允许POST请求' });
    }

    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    try {
        const { fileUrl, compoundId } = req.body;

        if (!fileUrl || !compoundId) {
            return res.status(400).json({ error: '缺少文件URL或化合物ID' });
        }

        // 下载CSV文件
        const response = await fetch(fileUrl);
        if (!response.ok) throw new Error(`无法下载文件: ${response.statusText}`);

        const csvContent = await response.text();

        // 解析CSV
        const rows = csvContent.trim().split('\n');
        const headers = rows[0].split(',');

        let x = [], y = [];

        // 检测是否有标题行
        let startRow = 0;
        if (headers[0].toLowerCase().includes('wavenumber')) {
            startRow = 1;
        }

        for (let i = startRow; i < rows.length; i++) {
            const [wn, t] = rows[i].split(',');
            if (!isNaN(parseFloat(wn)) && !isNaN(parseFloat(t))) {
                x.push(parseFloat(wn));
                y.push(parseFloat(t));
            }
        }

        if (x.length === 0) {
            throw new Error('CSV文件中没有有效数据');
        }

        // 创建JSON数据
        const jsonData = {
            name: compoundId.replace(/_/g, ' '),
            formula: '未知',
            x: x,
            y: y
        };

        // 上传到Supabase存储
        const jsonFileName = `${compoundId.replace(/[^a-zA-Z0-9]/g, '_')}.json`;
        const { data: uploadData, error: uploadError } = await supabase.storage
            .from('spectra-data')
            .upload(`processed/${jsonFileName}`, JSON.stringify(jsonData, null, 2), {
                contentType: 'application/json',
                upsert: true
            });

        if (uploadError) throw uploadError;

        // 更新数据库状态
        await supabase
            .from('compounds')
            .update({ is_hot: false })
            .eq('id', compoundId);

        res.status(200).json({
            success: true,
            message: '转换成功',
            data: jsonData
        });

    } catch (error) {
        console.error('❌ 转换失败:', error);
        res.status(500).json({ success: false, error: error.message });
    }
}
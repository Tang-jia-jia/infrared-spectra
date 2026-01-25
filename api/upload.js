// api/upload.js
import { createClient } from '@supabase/supabase-js';

// 初始化Supabase客户端（使用服务密钥，有完整权限）
const supabase = createClient(
    process.env.SUPABASE_URL,
    process.env.SUPABASE_SERVICE_KEY
);

export default async function handler(req, res) {
    // 只允许POST请求
    if (req.method !== 'POST') {
        return res.status(405).json({ error: '只允许POST请求' });
    }

    // 设置CORS头（允许跨域）
    res.setHeader('Access-Control-Allow-Origin', '*');
    res.setHeader('Access-Control-Allow-Methods', 'POST');
    res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

    if (req.method === 'OPTIONS') {
        return res.status(200).end();
    }

    try {
        console.log('收到上传请求:', req.body);

        const { fileName, fileData, formula } = req.body;

        // 验证请求数据
        if (!fileName || !fileData) {
            return res.status(400).json({ error: '缺少文件名或数据' });
        }

        // 清理文件名（移除特殊字符）
        const safeFileName = fileName.replace(/[^a-zA-Z0-9._-]/g, '_');
        const storagePath = `raw/${Date.now()}_${safeFileName}`;

        // 上传到Supabase存储（raw文件夹）
        const { data: uploadData, error: uploadError } = await supabase.storage
            .from('spectra-data')
            .upload(storagePath, Buffer.from(fileData, 'base64'), {
                contentType: 'text/csv',
                upsert: false  // 不覆盖已存在文件
            });

        if (uploadError) {
            console.error('上传错误:', uploadError);
            throw uploadError;
        }

        console.log('上传成功:', uploadData);

        // 获取文件公开URL
        const { data: urlData } = supabase.storage
            .from('spectra-data')
            .getPublicUrl(storagePath);

        const fileUrl = urlData.publicUrl;

        // 插入数据库记录
        const { data: dbData, error: dbError } = await supabase
            .from('compounds')
            .insert([
                {
                    name: fileName.replace('.csv', ''),  // 移除.csv后缀
                    formula: formula || '未知',
                    file_url: fileUrl,
                    is_hot: false  // 新上传默认为冷数据
                }
            ])
            .select()
            .single();

        if (dbError) {
            console.error('数据库错误:', dbError);
            throw dbError;
        }

        console.log('数据库记录成功:', dbData);

        // 返回成功响应
        res.status(200).json({
            success: true,
            message: '文件上传成功',
            data: dbData
        });

    } catch (error) {
        console.error('❌ 处理失败:', error);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
}
import { useEffect, useState } from 'react'
import { Upload, Button, List, Typography, message, Modal } from 'antd'
import { InboxOutlined, DeleteOutlined, FileTextOutlined } from '@ant-design/icons'
import type { UploadProps } from 'antd/es/upload/interface'
import { uploadFile, listFiles, deleteFile, type FileMetadata } from '../services/api'

const { Dragger } = Upload
const { Text } = Typography

interface FileUploadProps {
    visible: boolean
    onClose: () => void
}

export default function FileUpload({ visible, onClose }: FileUploadProps) {
    const [fileList, setFileList] = useState<FileMetadata[]>([])
    const [loading, setLoading] = useState(false)

    const fetchFiles = async () => {
        try {
            setLoading(true)
            const files = await listFiles()
            setFileList(files)
        } catch (error) {
            message.error('Failed to load files')
        } finally {
            setLoading(false)
        }
    }

    useEffect(() => {
        if (visible) {
            fetchFiles()
        }
    }, [visible])

    const handleUpload = async (options: any) => {
        const { file, onSuccess, onError } = options
        try {
            await uploadFile(file)
            message.success(`${file.name} uploaded successfully`)
            onSuccess("ok")
            fetchFiles()
        } catch (error) {
            message.error(`${file.name} upload failed`)
            onError(error)
        }
    }

    const handleDelete = async (id: string) => {
        try {
            await deleteFile(id)
            message.success('File deleted')
            fetchFiles()
        } catch (error) {
            message.error('Failed to delete file')
        }
    }

    const props: UploadProps = {
        name: 'file',
        multiple: true,
        customRequest: handleUpload,
        showUploadList: false,
        accept: '.pdf,.md,.txt,.py,.json,.yaml',
    }

    return (
        <Modal
            title="Knowledge Base Uploads"
            open={visible}
            onCancel={onClose}
            footer={null}
            width={600}
        >
            <div style={{ marginBottom: 16 }}>
                <Dragger {...props}>
                    <p className="ant-upload-drag-icon">
                        <InboxOutlined />
                    </p>
                    <p className="ant-upload-text">Click or drag file to this area to upload</p>
                    <p className="ant-upload-hint">
                        Support for PDF, Markdown, Text, Python, JSON, YAML.
                        Files will be indexed for RAG.
                    </p>
                </Dragger>
            </div>

            <List
                loading={loading}
                itemLayout="horizontal"
                dataSource={fileList}
                renderItem={(item) => (
                    <List.Item
                        actions={[
                            <Button
                                key="delete"
                                type="text"
                                danger
                                icon={<DeleteOutlined />}
                                onClick={() => handleDelete(item.file_id)}
                            />
                        ]}
                    >
                        <List.Item.Meta
                            avatar={<FileTextOutlined style={{ fontSize: 24, color: '#1890ff' }} />}
                            title={item.original_name}
                            description={
                                <Text type="secondary" style={{ fontSize: 12 }}>
                                    {(item.size_bytes / 1024).toFixed(1)} KB • {new Date(item.upload_time).toLocaleString()}
                                </Text>
                            }
                        />
                    </List.Item>
                )}
            />
        </Modal>
    )
}
